""" Ahjo MSI installer builder"""

import sys
import os
from sysconfig import get_platform

from cx_Freeze import Executable, setup
from sysconfig import get_platform

from ahjo.version import version as ahjo_version

# If the value in the named env var is set to "system" (case-insensitive),
# a system ("all users") MSI installer will be created.
# Any other or missing value creates a user installer ("single user").
# The final installer name will be suffixed with "-SYSTEM" or "-USER" respectively.
MSI_TARGET_TYPE_ENV_VAR = "AHJO_MSI_TARGET_TYPE"

# Application information
name = "Ahjo"
version = ahjo_version
author = "ALM Partners"
author_email = "servicedesk@almpartners.fi"
url = "https://github.com/ALMPartners/ahjo"
description = "Database deployment framework."

# Specify the GUID (DO NOT CHANGE ON UPGRADE)
# This has been obtained using:
# >>> import uuid
# >>> str(uuid.uuid3(uuid.NAMESPACE_DNS, 'ahjo.almpartners.fi')).upper()
upgrade_code = "{9D24F6F6-A1BB-3F84-9BF6-029ECE8F3DD6}"

programfiles_dir = (
    "ProgramFiles64Folder" if get_platform() == "win-amd64" else "ProgramFilesFolder"
)

include_files = ["src/ahjo/resources"]

# Packages to include and exclude with built executable

build_exe_options = {
    "packages": ["ahjo", "azure.identity"],
    "excludes": ["tkinter", "pip", "setuptools"],
    "includes": ["distutils.version", "pyodbc"],
    "include_msvcr": True,  # Include the Microsoft Visual C runtime files without needing the redistributable package installed
    "include_files": include_files
}

# Installable distribution options
installer_type = os.getenv(MSI_TARGET_TYPE_ENV_VAR, "user").strip().lower()
installer_type_suffix = "system" if installer_type == "system" else "user"
target_name = "AHJO-%s-%s-%s.msi" % (
    version,
    get_platform(),
    installer_type_suffix.upper(),
)
bdist_msi_options = {
    "all_users": installer_type == "system",
    "target_name": target_name,
    "upgrade_code": upgrade_code,
    "add_to_path": True,
    "initial_target_dir": "[%s]\%s\%s" % (programfiles_dir, author, name),
}

options = {"build_exe": build_exe_options, "bdist_msi": bdist_msi_options}

base = "Win32GUI" if sys.platform == "win32" else None
icon = "icon.ico"

ahjo_exe_prefix = "ahjo" 

ahjo_main_exe = Executable(
    "src/ahjo/scripts/master.py",
    target_name=f"{ahjo_exe_prefix}.exe", 
    base=None,
    icon=icon,
)

ahjo_init_project_exe = Executable(
    "src/ahjo/scripts/init_project.py",
    target_name=f"{ahjo_exe_prefix}-init-project.exe", 
    base=None,
    icon=icon,
)

ahjo_multi_project_build_exe = Executable(
    "src/ahjo/scripts/multi_project_build.py",
    target_name=f"{ahjo_exe_prefix}-multi-project-build.exe", 
    base=None,
    icon=icon,
)

ahjo_upgrade_exe = Executable(
    "src/ahjo/scripts/upgrade_project.py",
    target_name=f"{ahjo_exe_prefix}-upgrade.exe", 
    base=None,
    icon=icon,
)

ahjo_scan_exe = Executable(
    "src/ahjo/scripts/scan_project.py",
    target_name=f"{ahjo_exe_prefix}-scan.exe", 
    base=None,
    icon=icon,
)

ahjo_install_git_hook_exe = Executable(
    "src/ahjo/scripts/install_git_hook.py",
    target_name=f"{ahjo_exe_prefix}-install-git-hook.exe", 
    base=None,
    icon=icon,
)

ahjo_config_exe = Executable(
    "src/ahjo/scripts/config.py",
    target_name=f"{ahjo_exe_prefix}-config.exe", 
    base=None,
    icon=icon,
)

setup(
    name=name,
    version=version,
    author=author,
    author_email=author_email,
    url=url,
    description=description,
    options=options,
    executables=[
        ahjo_main_exe, 
        ahjo_init_project_exe, 
        ahjo_multi_project_build_exe, 
        ahjo_upgrade_exe, 
        ahjo_scan_exe,
        ahjo_install_git_hook_exe,
        ahjo_config_exe
    ],
)