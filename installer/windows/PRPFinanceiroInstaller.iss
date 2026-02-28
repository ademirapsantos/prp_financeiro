#define MyAppName "PRP Financeiro"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "PRP"
#define MyAppExeName "instalar_prp.bat"

[Setup]
AppId={{9B8B6717-3B15-4D93-B0E5-0C9EDB383C1A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\PRP Financeiro
DefaultGroupName=PRP Financeiro
AllowNoIcons=yes
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
OutputDir=.
OutputBaseFilename=PRPFinanceiro-Setup
DisableProgramGroupPage=yes

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "..\..\docker-compose.prod.yml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\docker-compose.prod.override.yml"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\.env.prod.example"; DestDir: "{app}"; Flags: ignoreversion
Source: "install.ps1"; DestDir: "{app}\installer\windows"; Flags: ignoreversion
Source: "instalar_prp.bat"; DestDir: "{app}\installer\windows"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}\installer"; Flags: ignoreversion

[Icons]
Name: "{group}\Instalar PRP Financeiro"; Filename: "{app}\installer\windows\instalar_prp.bat"
Name: "{group}\Pasta da Aplicacao"; Filename: "{app}"
Name: "{autodesktop}\Instalar PRP Financeiro"; Filename: "{app}\installer\windows\instalar_prp.bat"; Tasks: desktopicon

[Run]
Filename: "{app}\installer\windows\instalar_prp.bat"; Description: "Executar instalacao agora"; Flags: postinstall shellexec skipifsilent

[UninstallRun]
Filename: "powershell.exe"; Parameters: "-NoProfile -ExecutionPolicy Bypass -Command ""if (Get-Command docker -ErrorAction SilentlyContinue) { docker compose --env-file '{app}\.env.prod' -f '{app}\docker-compose.prod.yml' -f '{app}\docker-compose.prod.override.yml' down }"""; RunOnceId: "PRPComposeDown"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\runtime"

[Code]
var
  NetworkPage: TInputQueryWizardPage;

function TrimHost(const Value: string): string;
var
  S: string;
  P: Integer;
begin
  S := Trim(Value);
  if Pos('http://', Lowercase(S)) = 1 then
    Delete(S, 1, Length('http://'))
  else if Pos('https://', Lowercase(S)) = 1 then
    Delete(S, 1, Length('https://'));

  while (Length(S) > 0) and (S[Length(S)] = '/') do
    Delete(S, Length(S), 1);

  P := Pos('/', S);
  if P > 0 then
    S := Copy(S, 1, P - 1);

  Result := S;
end;

function IsLikelyIPv4(const S: string): Boolean;
var
  I, DotCount: Integer;
begin
  Result := False;
  DotCount := 0;
  if S = '' then
    Exit;

  for I := 1 to Length(S) do
  begin
    if S[I] = '.' then
      DotCount := DotCount + 1
    else if not ((S[I] >= '0') and (S[I] <= '9')) then
      Exit;
  end;

  Result := DotCount = 3;
end;

function InferBindIp(const PublicHost: string): string;
var
  L: string;
begin
  L := Lowercase(PublicHost);
  if (L = 'localhost') or (Pos('127.', L) = 1) then
    Result := '127.0.0.1'
  else if IsLikelyIPv4(PublicHost) then
    Result := PublicHost
  else
    Result := '0.0.0.0';
end;

function UpsertEnvLine(const FileName, Key, Value: string): Boolean;
var
  Lines: TArrayOfString;
  I, N: Integer;
  Prefix: string;
  Found: Boolean;
begin
  if FileExists(FileName) then
    LoadStringsFromFile(FileName, Lines)
  else
    SetArrayLength(Lines, 0);

  Prefix := Key + '=';
  Found := False;
  N := GetArrayLength(Lines);

  for I := 0 to N - 1 do
  begin
    if Pos(Prefix, Lines[I]) = 1 then
    begin
      Lines[I] := Prefix + Value;
      Found := True;
      Break;
    end;
  end;

  if not Found then
  begin
    SetArrayLength(Lines, N + 1);
    Lines[N] := Prefix + Value;
  end;

  Result := SaveStringsToFile(FileName, Lines, False);
end;

procedure InitializeWizard;
begin
  NetworkPage := CreateInputQueryPage(
    wpSelectDir,
    'Configuracao de Rede',
    'Informe o endereco de acesso da aplicacao',
    'Digite o IP ou dominio que o cliente vai usar para acessar o PRP Financeiro.'
  );
  NetworkPage.Add('IP ou dominio (sem http/https):', False);
  NetworkPage.Values[0] := 'localhost';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  HostValue: string;
begin
  Result := True;
  if CurPageID = NetworkPage.ID then
  begin
    HostValue := TrimHost(NetworkPage.Values[0]);
    if HostValue = '' then
    begin
      MsgBox('Informe um IP ou dominio valido.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    NetworkPage.Values[0] := HostValue;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvFile, EnvExample, PublicHost, BindIp: string;
begin
  if CurStep <> ssPostInstall then
    Exit;

  PublicHost := TrimHost(NetworkPage.Values[0]);
  if PublicHost = '' then
    PublicHost := 'localhost';
  BindIp := InferBindIp(PublicHost);

  EnvFile := ExpandConstant('{app}\.env.prod');
  EnvExample := ExpandConstant('{app}\.env.prod.example');

  if (not FileExists(EnvFile)) and FileExists(EnvExample) then
    FileCopy(EnvExample, EnvFile, False);

  UpsertEnvLine(EnvFile, 'APP_PUBLIC_HOST', PublicHost);
  UpsertEnvLine(EnvFile, 'APP_BIND_IP', BindIp);
end;
