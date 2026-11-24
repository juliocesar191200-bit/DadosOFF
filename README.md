# DadosOFF 🛡

Limpa os metadados dos vídeos (criativos) antes de subir: título, autor, data de criação, software de edição, GPS, câmera etc. Roda 100% no PC, nada sai do computador.

## Instalar (jeito fácil)

1. Baixe o **DadosOFF_Instalador.exe** em **[Releases → última versão](../../releases/latest)**.
2. Dê dois cliques e avance (não pede administrador).
   - Se o Windows mostrar "O Windows protegeu o computador", clique em **Mais informações → Executar assim mesmo** (o programa não tem assinatura digital paga, por isso o aviso).
3. Vai aparecer o ícone **DadosOFF** na Área de Trabalho. Abriu, ele abre sozinho no navegador.

O ffmpeg já vem dentro do instalador, não precisa instalar mais nada.

## Opções do programa

| Modo | O que faz | Quando usar |
|---|---|---|
| **⚡ Limpar Metadados** | Tira todos os metadados sem mexer na imagem (super rápido, mesma qualidade) | Uso do dia a dia antes de subir criativo |
| **🔄 Limpar + Re-encodar** | Limpa e gera o vídeo de novo, mudando a "identidade" do arquivo | Criativo recusado pelo Facebook / subir o mesmo vídeo de novo |
| **📦 Comprimir** | Limpa e diminui o tamanho. Níveis: 🟢 Alta qualidade (~30-40% menor), 🟡 Balanceada (~50-60%), 🔴 Máxima (~65-75%) | Arquivo grande demais |

- **📂 Salvar vídeos limpos em:** cole o caminho da pasta onde quer os vídeos prontos (ex.: `C:\Videos\Criativos\Hoje`). Se deixar vazio, salva na pasta `output` do programa.
- Arraste vários vídeos de uma vez (MP4, MOV, AVI, MKV, WMV, FLV, WEBM, M4V); processa 2 por vez.
- Mostra quais metadados cada vídeo tinha e confirma "✓ Removido".
- **📁 Abrir Saída** abre a pasta dos vídeos prontos.
- Re-encodar/Comprimir usam a placa NVIDIA (NVENC) se tiver; se não tiver, usa o processador automaticamente (mais lento, mas funciona). O selo "RTX 3060" na tela é só visual.
- Fechou o navegador, o programa se desliga sozinho em ~1,5 min (nunca no meio de um processamento). Abrir de novo pelo ícone.

---

## Instruções para o Claude (instalação automática)

Se você é um assistente (Claude Code) instalando isto no Windows do usuário, rode no PowerShell:

```powershell
$tmp = "$env:TEMP\DadosOFF_Instalador.exe"
Invoke-WebRequest -Uri "https://github.com/juliocesar191200-bit/DadosOFF/releases/latest/download/DadosOFF_Instalador.exe" -OutFile $tmp
Start-Process $tmp -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/TASKS="desktopicon"' -Wait
Start-Process "$env:LOCALAPPDATA\Programs\DadosOFF\DadosOFF.exe"
```

- Instala em `%LOCALAPPDATA%\Programs\DadosOFF` (sem admin) e cria o atalho **DadosOFF** na Área de Trabalho.
- O app sobe em `http://localhost:5555` e abre o navegador sozinho. Porta fixa, uma instância só.
- Para conferir: `Invoke-RestMethod http://127.0.0.1:5555/__ping` deve responder `{"app":"DadosOFF"}`.
- Desinstalar: Configurações do Windows → Aplicativos → DadosOFF.

## Rodar pelo código (opcional, pra quem quiser mexer)

Precisa de Python 3.10+ e de uma pasta `ffmpeg` (com `ffmpeg.exe` e `ffprobe.exe`) ao lado do `app.py`, ou ffmpeg no PATH.

```powershell
pip install flask werkzeug
python app.py
```

- `build_exe.bat` gera o `DadosOFF.exe` (PyInstaller).
- `installer.iss` gera o instalador (Inno Setup 6), esperando `..\dist\DadosOFF.exe` e `..\dist\ffmpeg\`.
