[Setup]
AppName=DadosOFF
AppVersion=1.3
AppPublisher=DadosOFF
DefaultDirName={autopf}\DadosOFF
DefaultGroupName=DadosOFF
OutputDir=installer_output
OutputBaseFilename=DadosOFF_Instalador
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName=DadosOFF
DisableProgramGroupPage=yes
PrivilegesRequired=lowest

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar ícone na Área de Trabalho"; GroupDescription: "Ícones adicionais:"

[Files]
Source: "..\dist\DadosOFF.exe";   DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\ffmpeg\*";       DestDir: "{app}\ffmpeg"; Flags: ignoreversion recursesubdirs

[Icons]
Name: "{autodesktop}\DadosOFF"; Filename: "{app}\DadosOFF.exe"; Tasks: desktopicon
Name: "{group}\DadosOFF";       Filename: "{app}\DadosOFF.exe"
Name: "{group}\Desinstalar DadosOFF"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\DadosOFF.exe"; Description: "Abrir DadosOFF agora"; Flags: nowait postinstall skipifsilent
