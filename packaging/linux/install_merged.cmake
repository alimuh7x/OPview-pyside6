# install_merged.cmake - installs OPView's frozen _internal/ tree flat into
# the lib/ it shares with OPStudio, skipping every Qt6 library some other
# install rule (OPStudio's Qt deploy) already put there, so the merged lib/
# carries a single copy of each. Included from a deferred install(CODE) rule
# in ../../CMakeLists.txt, which runs after OPStudio's own install rules.
#
# It also skips OPView's private copies of system libraries (libstdc++,
# OpenSSL, X11/xcb, ...) that OPStudio's installed binaries load from the
# system: those binaries search lib/ first ($ORIGIN rpaths), so a copy
# frozen on the build distro would shadow the newer system library on a
# newer distro (libOPCore picked up OPView's OpenSSL 3.0 on Ubuntu 26.04).
# Without its copy, OPView uses the same system library.
#
# Variables: OPVIEW_INTERNAL (frozen dist/OPView/_internal),
#            OPVIEW_LIBDIR, OPVIEW_BINDIR (relative to the prefix)
set(dest "${CMAKE_INSTALL_PREFIX}/${OPVIEW_LIBDIR}")
# file(INSTALL) prepends DESTDIR itself; the existence checks have to too
set(dest_on_disk "$ENV{DESTDIR}${dest}")

# PyInstaller puts a top-level symlink for every collected Qt6 lib, so the
# top level alone names every Qt6 lib OPView needs.
file(GLOB qt_libs RELATIVE "${OPVIEW_INTERNAL}" "${OPVIEW_INTERNAL}/libQt6*.so*")
set(excludes "")
set(shared "")
foreach(name IN LISTS qt_libs)
    set(existing "${dest_on_disk}/${name}")
    if(NOT EXISTS "${existing}")
        continue()
    endif()
    # OPView's own symlink, left by an earlier install into the same prefix,
    # is not a copy someone else provides
    if(IS_SYMLINK "${existing}")
        file(READ_SYMLINK "${existing}" target)
        if(target MATCHES "^PySide6/")
            continue()
        endif()
    endif()
    # PATTERN matches the basename anywhere in the tree, so this also drops
    # PySide6/Qt/lib/<name> - the copy PySide6's own modules would load first
    list(APPEND excludes PATTERN "${name}" EXCLUDE)
    list(APPEND shared "${name}")
    # and a stale copy of it from an earlier install would still win there
    file(REMOVE "${dest_on_disk}/PySide6/Qt/lib/${name}")
endforeach()
list(LENGTH shared n_shared)
message(STATUS "OPView: sharing ${n_shared} already-installed Qt6 libraries: ${shared}")

# Everything already in lib/ and bin/ was installed by OPStudio - this runs
# last. Collect what those files load (DT_NEEDED), leaving out OPView's own
# files from an earlier install into the same prefix.
file(GLOB opview_top RELATIVE "${OPVIEW_INTERNAL}" "${OPVIEW_INTERNAL}/*")
file(GLOB installed_files
    "${dest_on_disk}/*" "$ENV{DESTDIR}${CMAKE_INSTALL_PREFIX}/${OPVIEW_BINDIR}/*")
set(needed "")
foreach(f IN LISTS installed_files)
    get_filename_component(name "${f}" NAME)
    if(IS_DIRECTORY "${f}" OR name IN_LIST opview_top OR name STREQUAL "OPView")
        continue()
    endif()
    execute_process(COMMAND readelf -d "${f}"
        OUTPUT_VARIABLE dyn ERROR_QUIET RESULT_VARIABLE rc)
    if(NOT rc EQUAL 0)
        continue()
    endif()
    string(REGEX MATCHALL "\\(NEEDED\\)[^[]*\\[[^]]+\\]" entries "${dyn}")
    foreach(e IN LISTS entries)
        string(REGEX REPLACE ".*\\[([^]]+)\\]" "\\1" lib "${e}")
        list(APPEND needed "${lib}")
    endforeach()
endforeach()
list(REMOVE_DUPLICATES needed)
set(system_libs "")
foreach(name IN LISTS opview_top)
    if(name IN_LIST needed AND NOT EXISTS "${dest_on_disk}/${name}"
            AND NOT IS_DIRECTORY "${OPVIEW_INTERNAL}/${name}")
        list(APPEND excludes PATTERN "${name}" EXCLUDE)
        list(APPEND system_libs "${name}")
    endif()
endforeach()
list(LENGTH system_libs n_system)
message(STATUS "OPView: using the system's copy of ${n_system} libraries OPStudio loads: ${system_libs}")

file(INSTALL DESTINATION "${dest}" TYPE DIRECTORY FILES "${OPVIEW_INTERNAL}/"
    USE_SOURCE_PERMISSIONS ${excludes})
