# 3.22 = Ubuntu 22.04's apt cmake; needed features: file(CHMOD) 3.19,
# find_package version ranges 3.19, DEB zstd compression 3.22
cmake_minimum_required(VERSION 3.22)

#-----------------------------------------------------------------------------
# Standalone vs. embedded in the OPStudio superproject
#-----------------------------------------------------------------------------
if(NOT DEFINED PROJECT_NAME)
    set(OPVIEW_STANDALONE TRUE)
endif()

set(OPVIEW_VERSION "" CACHE STRING "OPView package version (default 2.1.0, or inherited from OPStudio)")
if(NOT OPVIEW_VERSION)
    if(DEFINED OPStudio_VERSION)
        set(OPVIEW_VERSION ${OPStudio_VERSION})
    else()
        set(OPVIEW_VERSION "2.1.0")
    endif()
endif()

project(OPView VERSION ${OPVIEW_VERSION} LANGUAGES NONE)

# Embedded: already included (and cached) by the OPStudio superproject before
# add_subdirectory(external) - this is then a no-op. Standalone: this is the
# only place CMAKE_INSTALL_BINDIR/LIBDIR/DATAROOTDIR get defined for the
# install() rules below.
include(GNUInstallDirs)

#-----------------------------------------------------------------------------
# Python discovery (Python 3.14 needs vtk >= 9.6.2 for cp314 wheels)
#-----------------------------------------------------------------------------
set(OPVIEW_PYTHON_EXECUTABLE "" CACHE FILEPATH "Python interpreter used to create the freeze venv")
if(NOT OPVIEW_PYTHON_EXECUTABLE)
    find_package(Python3 3.10...<3.15 COMPONENTS Interpreter REQUIRED)
    set(OPVIEW_PYTHON_EXECUTABLE ${Python3_EXECUTABLE})
endif()
message(STATUS "OPView freeze Python: ${OPVIEW_PYTHON_EXECUTABLE}")

set(OPVIEW_VENV ${CMAKE_CURRENT_BINARY_DIR}/pyi-venv)
if(WIN32)
    set(OPVIEW_VENV_PY ${OPVIEW_VENV}/Scripts/python.exe)
else()
    set(OPVIEW_VENV_PY ${OPVIEW_VENV}/bin/python)
endif()

#-----------------------------------------------------------------------------
# 1) Virtual environment
#-----------------------------------------------------------------------------
add_custom_command(OUTPUT ${OPVIEW_VENV_PY}
    COMMAND ${OPVIEW_PYTHON_EXECUTABLE} -m venv ${OPVIEW_VENV}
    COMMENT "Creating PyInstaller venv"
)

#-----------------------------------------------------------------------------
# 2) Python dependencies (re-runs when requirements.txt changes)
#-----------------------------------------------------------------------------
set(PIP_STAMP ${CMAKE_CURRENT_BINARY_DIR}/pip-install.stamp)
add_custom_command(OUTPUT ${PIP_STAMP}
    COMMAND ${OPVIEW_VENV_PY} -m pip install --upgrade pip
    COMMAND ${OPVIEW_VENV_PY} -m pip install -r ${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt
            "pyinstaller>=6.10" "pyinstaller-hooks-contrib>=2025.0"
    COMMAND ${CMAKE_COMMAND} -E touch ${PIP_STAMP}
    DEPENDS ${OPVIEW_VENV_PY} ${CMAKE_CURRENT_SOURCE_DIR}/requirements.txt
    COMMENT "Installing Python dependencies + PyInstaller"
)

#-----------------------------------------------------------------------------
# 3) version.txt baked into the bundle (read by app/version.py)
#-----------------------------------------------------------------------------
set(OPVIEW_VERSION_FILE ${CMAKE_CURRENT_BINARY_DIR}/version.txt)
file(WRITE ${OPVIEW_VERSION_FILE} "${OPVIEW_VERSION}\n")

#-----------------------------------------------------------------------------
# 4) PyInstaller freeze (onedir)
#-----------------------------------------------------------------------------
file(GLOB_RECURSE OPVIEW_PY_SOURCES CONFIGURE_DEPENDS
    ${CMAKE_CURRENT_SOURCE_DIR}/main.py
    ${CMAKE_CURRENT_SOURCE_DIR}/app/*.py
    ${CMAKE_CURRENT_SOURCE_DIR}/config/*.py
    ${CMAKE_CURRENT_SOURCE_DIR}/data/*.py
    ${CMAKE_CURRENT_SOURCE_DIR}/graphs/*.py
    ${CMAKE_CURRENT_SOURCE_DIR}/multi_view/*.py
    ${CMAKE_CURRENT_SOURCE_DIR}/sidebar/*.py
    ${CMAKE_CURRENT_SOURCE_DIR}/single_view/*.py
    ${CMAKE_CURRENT_SOURCE_DIR}/utils/*.py
    ${CMAKE_CURRENT_SOURCE_DIR}/viewer/*.py
)
set(OPVIEW_DIST ${CMAKE_CURRENT_BINARY_DIR}/dist/OPView)
# Promote to the top-level scope: opview_dll_collision_check (top-level
# CMakeLists.txt) needs this path but sits outside this directory's scope.
set(OPVIEW_DIST ${OPVIEW_DIST} CACHE INTERNAL "OPView PyInstaller onedir dist directory")
if(WIN32)
    set(OPVIEW_EXE ${OPVIEW_DIST}/OPView.exe)
else()
    set(OPVIEW_EXE ${OPVIEW_DIST}/OPView)
endif()
set(OPVIEW_FREEZE_EXTRA_COMMAND "")
if(UNIX AND NOT APPLE)
    # PyInstaller's own dependency analysis doesn't reach every private
    # vendored .so (e.g. numpy.libs/scipy.libs copies, or libs only reachable
    # through a dlopen'd Qt plugin like libqtiff.so) - a bare `ldd` (as
    # OPStudio's deb-install CI check runs) can't resolve those, since it
    # doesn't see the bootloader's runtime-injected LD_LIBRARY_PATH. Patch an
    # additive $ORIGIN rpath onto every frozen file after the freeze so they
    # resolve without relying on that env var.
    find_program(PATCHELF patchelf)
    if(NOT PATCHELF)
        message(FATAL_ERROR "patchelf not found - required to fix rpaths in the frozen OPView bundle (see packaging/linux/fix_rpaths.sh)")
    endif()
    set(OPVIEW_FIX_RPATHS_SCRIPT ${CMAKE_CURRENT_SOURCE_DIR}/packaging/linux/fix_rpaths.sh)
    set(OPVIEW_FREEZE_EXTRA_COMMAND
        COMMAND bash ${OPVIEW_FIX_RPATHS_SCRIPT} ${OPVIEW_DIST})
endif()
add_custom_command(OUTPUT ${OPVIEW_EXE}
    COMMAND ${CMAKE_COMMAND} -E env OPVIEW_VERSION_FILE=${OPVIEW_VERSION_FILE}
            ${OPVIEW_VENV_PY} -m PyInstaller --noconfirm --clean
            --distpath ${CMAKE_CURRENT_BINARY_DIR}/dist
            --workpath ${CMAKE_CURRENT_BINARY_DIR}/pyi-build
            ${CMAKE_CURRENT_SOURCE_DIR}/packaging/opview.spec
    ${OPVIEW_FREEZE_EXTRA_COMMAND}
    DEPENDS ${PIP_STAMP} ${OPVIEW_PY_SOURCES}
            ${CMAKE_CURRENT_SOURCE_DIR}/packaging/opview.spec
            ${OPVIEW_VERSION_FILE}
            ${OPVIEW_FIX_RPATHS_SCRIPT}
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Freezing OPView with PyInstaller (onedir)"
)
add_custom_target(opview_freeze ALL DEPENDS ${OPVIEW_EXE})

#-----------------------------------------------------------------------------
# Install rules (component 'opview' everywhere for superproject reuse)
#-----------------------------------------------------------------------------
if(WIN32)
    # Standalone: flat layout so CPACK_NSIS_INSTALLED_ICON_NAME (OPView.exe at
    # $INSTDIR root) resolves. Embedded: install into OPStudio's own
    # ${CMAKE_INSTALL_BINDIR} (GNUInstallDirs, set by the superproject) so
    # OPView.exe sits alongside OPStudio.exe like every other installed
    # binary in this codebase. This merges OPView's bundled DLL closet (Qt6,
    # VTK, Python runtime) into the same directory as OPStudio's own
    # (Qt5, oneAPI) - a deliberate tradeoff for GNUInstallDirs consistency;
    # see the opview_dll_collision_check target in the top-level
    # CMakeLists.txt for the safety net against filename collisions.
    if(OPVIEW_STANDALONE)
        set(OPVIEW_WIN_INSTALL_DESTINATION .)
    else()
        set(OPVIEW_WIN_INSTALL_DESTINATION ${CMAKE_INSTALL_BINDIR})
    endif()
    install(DIRECTORY ${OPVIEW_DIST}/ DESTINATION ${OPVIEW_WIN_INSTALL_DESTINATION}
        USE_SOURCE_PERMISSIONS COMPONENT opview)
else()
    install(DIRECTORY ${OPVIEW_DIST}/ DESTINATION ${CMAKE_INSTALL_LIBDIR}/opview
        USE_SOURCE_PERMISSIONS COMPONENT opview)
    install(PROGRAMS packaging/linux/opview DESTINATION ${CMAKE_INSTALL_BINDIR} COMPONENT opview)
    install(FILES packaging/linux/opview.desktop
        DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/applications COMPONENT opview)
    install(FILES assets/OP_Logo.png
        DESTINATION ${CMAKE_INSTALL_DATAROOTDIR}/pixmaps RENAME opview.png COMPONENT opview)
endif()

#-----------------------------------------------------------------------------
# Tests
#-----------------------------------------------------------------------------
enable_testing()
add_test(NAME opview_frozen_version COMMAND ${OPVIEW_EXE} --version)
set_tests_properties(opview_frozen_version PROPERTIES
    ENVIRONMENT "QT_QPA_PLATFORM=offscreen"
    TIMEOUT 120
)
add_test(NAME opview_unittests
    COMMAND ${OPVIEW_VENV_PY} -m unittest discover tests
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)
set_tests_properties(opview_unittests PROPERTIES
    # QTWEBENGINE_DISABLE_SANDBOX: CI runners execute tests as root, and
    # Chromium's sandbox refuses to initialize under root without it.
    ENVIRONMENT "QT_QPA_PLATFORM=offscreen;QTWEBENGINE_DISABLE_SANDBOX=1"
    TIMEOUT 600
)
if(UNIX AND NOT APPLE)
    # Catches missing-shared-library regressions (private vendored libs with
    # no rpath, or a system lib PyInstaller's collector didn't bundle) right
    # here at freeze time, on the one platform (ubuntu:22.04) these builds
    # happen on - instead of only downstream, several build cycles later, in
    # OPStudio's cross-distro `test:deb-install` CI matrix. Deliberately runs
    # `ldd` with no LD_LIBRARY_PATH set, matching how that downstream check
    # inspects the installed tree (a plain `ldd <file>`, not an app launch).
    # NOTE: `find -exec cmd \;`'s own exit status does NOT reflect cmd's exit
    # status, so failure detection must go through captured output (grep),
    # not the exec'd command's exit code - the same idiom OPStudio's
    # test:deb-install CI job uses for the equivalent installed-tree check.
    add_test(NAME opview_frozen_no_missing_libs
        COMMAND bash -c "MISSING=$(find '${OPVIEW_DIST}' -type f -exec ldd {} \\; 2>/dev/null | grep -i 'not found' | sort -u || true); if [ -n \"$MISSING\" ]; then echo \"$MISSING\"; exit 1; fi"
    )
endif()

#-----------------------------------------------------------------------------
# AppImage (Linux, explicit target — mirrors OPStudio's 'appimage' target;
# uses appimagetool, NOT linuxdeployqt: the PyInstaller bundle already ships
# its own Qt and must not be re-deployed/patched)
#-----------------------------------------------------------------------------
if(UNIX AND NOT APPLE)
    set(OPVIEW_APPIMAGETOOL "" CACHE FILEPATH "Path to appimagetool (downloaded automatically if empty)")
    if(NOT OPVIEW_APPIMAGETOOL)
        find_program(_APPIMAGETOOL_ON_PATH appimagetool)
        if(_APPIMAGETOOL_ON_PATH)
            set(OPVIEW_APPIMAGETOOL ${_APPIMAGETOOL_ON_PATH})
        else()
            set(OPVIEW_APPIMAGETOOL ${CMAKE_CURRENT_BINARY_DIR}/appimagetool-x86_64.AppImage)
            if(NOT EXISTS ${OPVIEW_APPIMAGETOOL})
                message(STATUS "Downloading appimagetool")
                file(DOWNLOAD
                    https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
                    ${OPVIEW_APPIMAGETOOL}
                    SHOW_PROGRESS STATUS _dl_status
                )
                list(GET _dl_status 0 _dl_code)
                if(NOT _dl_code EQUAL 0)
                    file(REMOVE ${OPVIEW_APPIMAGETOOL})
                    message(WARNING "appimagetool download failed; the opview_appimage target will not work until -DOPVIEW_APPIMAGETOOL is provided")
                endif()
            endif()
            if(EXISTS ${OPVIEW_APPIMAGETOOL})
                file(CHMOD ${OPVIEW_APPIMAGETOOL} PERMISSIONS
                    OWNER_READ OWNER_WRITE OWNER_EXECUTE
                    GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE)
            endif()
        endif()
    endif()

    set(PACKAGES_DIR ${CMAKE_CURRENT_BINARY_DIR}/packages)
    set(OPVIEW_APPDIR ${CMAKE_CURRENT_BINARY_DIR}/AppDir)
    set(OPVIEW_APPIMAGE_NAME OPView-${OPVIEW_VERSION}-x86_64.AppImage)
    add_custom_target(opview_appimage
        COMMAND ${CMAKE_COMMAND} -E echo "=== [appimage] Staging AppDir ==="
        COMMAND ${CMAKE_COMMAND} -E rm -rf ${OPVIEW_APPDIR}
        COMMAND ${CMAKE_COMMAND} -E make_directory ${OPVIEW_APPDIR}/usr/lib
        COMMAND ${CMAKE_COMMAND} -E copy_directory ${OPVIEW_DIST} ${OPVIEW_APPDIR}/usr/lib/opview
        # copy_directory does not preserve exec bits -> restore them
        COMMAND chmod +x ${OPVIEW_APPDIR}/usr/lib/opview/OPView
        COMMAND chmod +x ${OPVIEW_APPDIR}/usr/lib/opview/_internal/PySide6/Qt/libexec/QtWebEngineProcess
        COMMAND ${CMAKE_COMMAND} -E copy
                ${CMAKE_CURRENT_SOURCE_DIR}/packaging/linux/AppRun ${OPVIEW_APPDIR}/AppRun
        COMMAND chmod +x ${OPVIEW_APPDIR}/AppRun
        COMMAND ${CMAKE_COMMAND} -E copy
                ${CMAKE_CURRENT_SOURCE_DIR}/packaging/linux/opview.desktop ${OPVIEW_APPDIR}/opview.desktop
        COMMAND ${CMAKE_COMMAND} -E copy
                ${CMAKE_CURRENT_SOURCE_DIR}/assets/OP_Logo.png ${OPVIEW_APPDIR}/opview.png
        COMMAND ${CMAKE_COMMAND} -E make_directory ${PACKAGES_DIR}
        COMMAND ${CMAKE_COMMAND} -E echo "=== [appimage] Running appimagetool ==="
        COMMAND ${CMAKE_COMMAND} -E env VERSION=${OPVIEW_VERSION} ARCH=x86_64
                ${OPVIEW_APPIMAGETOOL} --appimage-extract-and-run
                ${OPVIEW_APPDIR} ${PACKAGES_DIR}/${OPVIEW_APPIMAGE_NAME}
        COMMAND ${CMAKE_COMMAND} -E echo "=== [appimage] Done: ${PACKAGES_DIR}/${OPVIEW_APPIMAGE_NAME} ==="
        DEPENDS ${OPVIEW_EXE}
        WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}
    )
endif()

#-----------------------------------------------------------------------------
# CPack (standalone builds only; the superproject provides its own)
#-----------------------------------------------------------------------------
if(OPVIEW_STANDALONE)
    if(WIN32)
        set(CPACK_GENERATOR "NSIS")
        # LANGUAGES NONE means no compiler ever sets CMAKE_SIZEOF_VOID_P, so
        # CPack's own arch detection defaults to win32 even though the
        # bundled Python/PySide6/VTK are 64-bit.
        set(CPACK_SYSTEM_NAME "win64")
        # Same LANGUAGES NONE gap: CPack.cmake only defaults
        # CPACK_NSIS_INSTALL_ROOT to $PROGRAMFILES64 when CMAKE_SIZEOF_VOID_P
        # EQUAL 8, which never happens here - without this override the
        # installer silently targets Program Files (x86).
        set(CPACK_NSIS_INSTALL_ROOT "$PROGRAMFILES64")
    else()
        set(CPACK_GENERATOR "DEB")
    endif()
    set(CPACK_PACKAGE_NAME "OPView")
    set(CPACK_PACKAGE_VENDOR "OpenPhase Solutions GmbH")
    set(CPACK_PACKAGE_CONTACT "office@openphase-solutions.com")
    set(CPACK_PACKAGE_VERSION ${OPVIEW_VERSION})
    set(CPACK_PACKAGE_INSTALL_DIRECTORY "OPView")
    set(CPACK_PACKAGE_DESCRIPTION_SUMMARY "Viewer for OpenPhase simulation results")

    # Debian package
    set(CPACK_DEBIAN_PACKAGE_NAME "opview")
    set(CPACK_DEBIAN_FILE_NAME DEB-DEFAULT)
    set(CPACK_DEBIAN_PACKAGE_ARCHITECTURE "amd64")
    # dpkg-shlibdeps cannot process a PyInstaller tree (private bundled libs,
    # $ORIGIN rpaths) -> dependencies are listed by hand below
    set(CPACK_DEBIAN_PACKAGE_SHLIBDEPS OFF)
    set(CPACK_DEBIAN_PACKAGE_SECTION "science")
    set(CPACK_DEBIAN_PACKAGE_PRIORITY "optional")
    set(CPACK_DEBIAN_PACKAGE_MAINTAINER "OpenPhase Solutions GmbH <office@openphase-solutions.com>")
    set(CPACK_DEBIAN_PACKAGE_HOMEPAGE "https://www.openphase-solutions.com")
    # ~1 GB payload: zstd keeps packaging time reasonable (xz takes minutes)
    set(CPACK_DEBIAN_COMPRESSION_TYPE "zstd")
    # System libraries the PySide6/QtWebEngine + VTK bundle does not ship
    # (X11/xcb stack, Chromium NSS/GL/cups, GTK theme + audio codec stack);
    # '| t64' alternatives cover Ubuntu 24.04's time_t transition. Kept in
    # sync with the equivalent block in the superproject's top-level
    # CMakeLists.txt (opstudio/CMakeLists.txt, ENABLE_OPVIEW branch).
    #
    # libtiff.so.5/libpcre.so.3/libmpdec.so.3/libFLAC.so.8/libunistring.so.2
    # are deliberately NOT listed here (they're absent or ABI-incompatible
    # under those exact sonames on Ubuntu 24.04+, so no Depends string can
    # satisfy every supported target) - they travel bundled with the frozen
    # app instead (see packaging/build_linux_packages.sh and
    # packaging/linux/fix_rpaths.sh).
    set(CPACK_DEBIAN_PACKAGE_DEPENDS
        "libc6, libstdc++6, libgl1, libegl1, libopengl0, libglib2.0-0 | libglib2.0-0t64, libfontconfig1, libfreetype6, libdbus-1-3, libnss3, libnspr4, libasound2 | libasound2t64, libxkbcommon0, libxkbcommon-x11-0, libx11-6, libx11-xcb1, libxcb1, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render0, libxcb-render-util0, libxcb-shape0, libxcb-shm0, libxcb-sync1, libxcb-xfixes0, libxcb-xkb1, libxext6, libxcomposite1, libxdamage1, libxfixes3, libxrandr2, libxrender1, libxtst6, libxi6, libsm6, libice6, libdrm2, libgbm1, libcups2 | libcups2t64, libwayland-server0, libwayland-client0, libwayland-cursor0, libwayland-egl1")
    string(APPEND CPACK_DEBIAN_PACKAGE_DEPENDS
        ", libxkbfile1, libxcursor1, libxinerama1, libxres1, libgtk-3-0 | libgtk-3-0t64, liblcms2-2, libpulse0, libsndfile1, libopus0, libvorbisenc2, libogg0, libmpg123-0 | libmpg123-0t64, libmp3lame0, libseccomp2, libatomic1, libapparmor1, libwebp7, libjbig0, libdeflate0")
    set(CPACK_DEBIAN_PACKAGE_RECOMMENDS "fonts-liberation | fonts-dejavu-core")

    # NSIS installer
    set(CPACK_NSIS_DISPLAY_NAME "OPView")
    set(CPACK_NSIS_PACKAGE_NAME "OPView")
    set(CPACK_NSIS_CONTACT "office@openphase-solutions.com")
    set(CPACK_NSIS_URL_INFO_ABOUT "https://www.openphase-solutions.com")
    set(CPACK_NSIS_MUI_ICON "${CMAKE_CURRENT_SOURCE_DIR}/assets/OPView.ico")
    set(CPACK_NSIS_MUI_UNIICON "${CMAKE_CURRENT_SOURCE_DIR}/assets/OPView.ico")
    set(CPACK_NSIS_INSTALLED_ICON_NAME "OPView.exe")
    set(CPACK_NSIS_ENABLE_UNINSTALL_BEFORE_INSTALL ON)
    set(CPACK_NSIS_CREATE_ICONS_EXTRA
        "CreateShortCut \\\"$SMPROGRAMS\\\\$STARTMENU_FOLDER\\\\OPView.lnk\\\" \\\"$INSTDIR\\\\OPView.exe\\\""
    )
    set(CPACK_NSIS_DELETE_ICONS_EXTRA
        "Delete \\\"$SMPROGRAMS\\\\$STARTMENU_FOLDER\\\\OPView.lnk\\\""
    )

    include(CPack)
    set(CPACK_COMPONENTS_ALL opview)
    set(CPACK_COMPONENTS_GROUPING ALL_COMPONENTS_IN_ONE)
endif()
