!include MUI2.nsh

Name "Gmail Backup"
OutFile "inst_EXE\gmail-backup-installer.exe"
AllowRootDirInstall true
XPStyle on
; RequestExecutionLevel user
RequestExecutionLevel admin

SetCompressor /SOLID lzma

; The default installation directory
InstallDir "$PROGRAMFILES\GmailBackup"

; Registry key to check for directory (so if you install again, it will 
; overwrite the old one automatically)
InstallDirRegKey HKLM "Software\GmailBackup" "Install_Dir"

!define MUI_COMPONENTSPAGE_NODESC
Var StartMenuFolder

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE"
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_STARTMENU "Application" $StartMenuFolder
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_WELCOME
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

!insertmacro MUI_LANGUAGE "English" 
!insertmacro MUI_LANGUAGE "French"
!insertmacro MUI_LANGUAGE "German"
!insertmacro MUI_LANGUAGE "Spanish"
!insertmacro MUI_LANGUAGE "SpanishInternational"
!insertmacro MUI_LANGUAGE "SimpChinese"
!insertmacro MUI_LANGUAGE "TradChinese"
!insertmacro MUI_LANGUAGE "Japanese"
!insertmacro MUI_LANGUAGE "Korean"
!insertmacro MUI_LANGUAGE "Italian"
!insertmacro MUI_LANGUAGE "Dutch"
!insertmacro MUI_LANGUAGE "Danish"
!insertmacro MUI_LANGUAGE "Swedish"
!insertmacro MUI_LANGUAGE "Norwegian"
!insertmacro MUI_LANGUAGE "NorwegianNynorsk"
!insertmacro MUI_LANGUAGE "Finnish"
!insertmacro MUI_LANGUAGE "Greek"
!insertmacro MUI_LANGUAGE "Russian"
!insertmacro MUI_LANGUAGE "Portuguese"
!insertmacro MUI_LANGUAGE "PortugueseBR"
!insertmacro MUI_LANGUAGE "Polish"
!insertmacro MUI_LANGUAGE "Ukrainian"
!insertmacro MUI_LANGUAGE "Czech"
!insertmacro MUI_LANGUAGE "Slovak"
!insertmacro MUI_LANGUAGE "Croatian"
!insertmacro MUI_LANGUAGE "Bulgarian"
!insertmacro MUI_LANGUAGE "Hungarian"
!insertmacro MUI_LANGUAGE "Thai"
!insertmacro MUI_LANGUAGE "Romanian"
!insertmacro MUI_LANGUAGE "Latvian"
!insertmacro MUI_LANGUAGE "Macedonian"
!insertmacro MUI_LANGUAGE "Estonian"
!insertmacro MUI_LANGUAGE "Turkish"
!insertmacro MUI_LANGUAGE "Lithuanian"
!insertmacro MUI_LANGUAGE "Slovenian"
!insertmacro MUI_LANGUAGE "Serbian"
!insertmacro MUI_LANGUAGE "SerbianLatin"
!insertmacro MUI_LANGUAGE "Arabic"
!insertmacro MUI_LANGUAGE "Farsi"
!insertmacro MUI_LANGUAGE "Hebrew"
!insertmacro MUI_LANGUAGE "Indonesian"
!insertmacro MUI_LANGUAGE "Mongolian"
!insertmacro MUI_LANGUAGE "Luxembourgish"
!insertmacro MUI_LANGUAGE "Albanian"
!insertmacro MUI_LANGUAGE "Breton"
!insertmacro MUI_LANGUAGE "Belarusian"
!insertmacro MUI_LANGUAGE "Icelandic"
!insertmacro MUI_LANGUAGE "Malay"
!insertmacro MUI_LANGUAGE "Bosnian"
!insertmacro MUI_LANGUAGE "Kurdish"
!insertmacro MUI_LANGUAGE "Irish"
!insertmacro MUI_LANGUAGE "Uzbek"
!insertmacro MUI_LANGUAGE "Galician"
!insertmacro MUI_LANGUAGE "Afrikaans"
!insertmacro MUI_LANGUAGE "Catalan"

;--------------------------------
;Installer Functions

Section "Gmail Backup (required)"
  SectionIn RO

  SetOutPath "$INSTDIR"

  File "dist_EXE\*"

  SetOutPath "$INSTDIR\messages"
  File "dist_EXE\messages\*"

  SetOutPath "$INSTDIR\messages\cs_CZ\LC_MESSAGES"
  File "dist_EXE\messages\cs_CZ\LC_MESSAGES\*"

  SetOutPath "$INSTDIR\messages\ru_RU\LC_MESSAGES"
  File "dist_EXE\messages\ru_RU\LC_MESSAGES\*"

  SetOutPath "$INSTDIR\messages\nl\LC_MESSAGES"
  File "dist_EXE\messages\nl\LC_MESSAGES\*"

  SetOutPath "$INSTDIR\messages\da\LC_MESSAGES"
  File "dist_EXE\messages\da\LC_MESSAGES\*"

  ; Write the installation path into the registry
  WriteRegStr HKLM "Software\GmailBackup" "Install_Dir" "$INSTDIR"
  
  ; Write the uninstall keys for Windows
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\gmailbackup" "DisplayName" "Gmail Backup"
  WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\gmailbackup" "UninstallString" '"$INSTDIR\uninstall.exe"'
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\gmailbackup" "NoModify" 1
  WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\gmailbackup" "NoRepair" 1
  WriteUninstaller "uninstall.exe"
 
SectionEnd

;Function .onInit
;  !insertmacro MUI_LANGDLL_DISPLAY
;FunctionEnd

; Optional section (can be disabled by the user)
Section "Start Menu Shortcuts"
  SetShellVarContext all

  CreateDirectory "$SMPROGRAMS\Gmail Backup"
  CreateShortCut "$SMPROGRAMS\Gmail Backup\Uninstall.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe"
  CreateShortCut "$SMPROGRAMS\Gmail Backup\GMail Backup.lnk" "$INSTDIR\gmail-backup-gui.exe" "" "$INSTDIR\gmb.ico"
  CreateShortCut "$DESKTOP\GMail Backup.lnk" "$INSTDIR\gmail-backup-gui.exe" "" "$INSTDIR\gmb.ico"
SectionEnd

;--------------------------------

; Uninstaller

Section "Uninstall"
  SetShellVarContext all
  
  ; Remove registry keys
  DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\gmailbackup"
  DeleteRegKey HKLM SOFTWARE\gmailbackup

  ; Remove files and uninstaller
  Delete $INSTDIR\uninstall.exe

  ; Remove shortcuts, if any
  Delete "$SMPROGRAMS\Gmail Backup\*.*"
  Delete "$DESKTOP\GMail Backup.lnk"

  ; Remove directories used
  RMDir "$SMPROGRAMS\Gmail Backup"
  RMDir /r "$INSTDIR"

SectionEnd

;--------------------------------
;Uninstaller Functions

;Function un.onInit
;  !insertmacro MUI_UNGETLANGUAGE
;FunctionEnd
