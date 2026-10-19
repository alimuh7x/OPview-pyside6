# install_merged.cmake - installs OPView's frozen _internal/ tree flat into
# the lib/ it shares with OPStudio, skipping every Qt6 library some other
# install rule (OPStudio's Qt deploy) already put there, so the merged lib/
# carries a single copy of each. Included from a deferred install(CODE) rule
# in ../../CMakeLists.txt, which runs after OPStudio's own install rules.
#
# Variables: OPVIEW_INTERNAL (frozen dist/OPView/_internal),
#            OPVIEW_LIBDIR (CMAKE_INSTALL_LIBDIR, relative to the prefix)
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

file(INSTALL DESTINATION "${dest}" TYPE DIRECTORY FILES "${OPVIEW_INTERNAL}/"
    USE_SOURCE_PERMISSIONS ${excludes})
