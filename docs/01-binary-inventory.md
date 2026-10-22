# Inventário de binários — fase 1

Data da inspeção: 2026-10-21

## Arquivo fornecido

| Caminho | Tamanho | Formato / arquitetura | SHA-256 |
|---|---:|---|---|
| `ATTACK SHARK K86 SOFT.exe` | 101.868.672 bytes | PE32 GUI, Windows, x86; instalador NSIS 3 Unicode | `3ee70880c8b5adcd469a0e3ebefa7e280a22fa23ff74e369955511a2c58e04a2` |

Metadados do PE observados: ProductName `Attack Shark Driver v4`; FileVersion `3.1.12.0`; compilação PE datada de 2018-12-15, enquanto recursos/entradas do pacote indicam novembro de 2025. Esses campos são metadados distintos e não foram tratados como data comprovada de lançamento.

O EXE externo importa `KERNEL32.dll`, `USER32.dll`, `GDI32.dll`, `SHELL32.dll`, `ADVAPI32.dll`, `COMCTL32.dll` e `ole32.dll`. Entre as APIs importadas estão `CreateFileW`, `ReadFile`, `WriteFile`, `ShellExecuteExW` e operações de registro. Não há importação observada de `HID.dll`, `SetupAPI.dll` ou `WinUSB.dll` nesse stub do instalador. Isso descreve apenas o stub, não os componentes embarcados.

## Conteúdo NSIS e aplicação

`7z l` reconheceu o pacote como NSIS-3 Unicode e listou oito arquivos, incluindo `$PLUGINSDIR/app-32.7z` (101.361.720 bytes), `System.dll`, `StdUtils.dll`, `SpiderBanner.dll`, `nsExec.dll`, `nsis7z.dll`, `WinShell.dll` e o desinstalador. O arquivo interno foi extraído somente para `/tmp` para listar seu conteúdo; os originais foram preservados.

O pacote interno contém uma aplicação Electron e múltiplos recursos. Foram identificados:

| Componente | Observação |
|---|---|
| `Attack Shark Driver v4.exe` | PE32 GUI Windows x86, 136.257.536 bytes; SHA-256 `9a8a69394f94a23dc787662129852742ddd487d651c3f65dabeffe56439b2814` |
| `resources/app/package.json` | `name` Attack Shark Driver v4, versão 3.1.12, CommonJS; `main` aponta para `dist-electron/main.js` |
| `resources/app/dist-electron/main.js` | Processo principal Electron; cria janela, tray, ciclo de vida e IPC para preferências da janela/login |
| `resources/app/dist/` | Frontend compilado com JavaScript, CSS, fontes e imagens; os nomes de chunks sugerem bundle web compilado |
| `resources/app/iot_driver.exe` | Helper PE32 GUI Windows x86, 6.702.656 bytes; SHA-256 `ef43fd46fe8f9908cd71e15032b76390ee79bd67de78683facc2127eafe514b1` |
| `locales/`, arquivos Chromium/Electron | Dados do runtime, idiomas e licenças |

O pacote declara dependências JavaScript como React 18.2, `@electron/remote`, Axios, protobuf-ts/grpcweb, JSZip, Jimp e bibliotecas de UI. O executável principal empacotado confirma a entrega do runtime Electron/Chromium; não é uma aplicação .NET.

O bundle compilado contém uma fronteira local com o helper: cliente protobuf-ts gRPC-Web em `http://127.0.0.1:3814`. Os métodos encontrados incluem `sendMsg`, `sendRawFeature`, `readMsg`, `readRawFeature`, `cleanDev` e chamadas de enumeração/lista de dispositivos. O frontend prepara um helper versionado na pasta `userData`, copiando o `iot_driver.exe` empacotado quando necessário, e o fluxo de auto-connect reinicia/abre esse helper. A presença dessas rotas comprova a arquitetura de comunicação app → helper em loopback; não comprova o conteúdo de relatórios HID nem a semântica das funções para o K86.

O frontend genérico também contém estados/ações para remapeamento de teclas e camada Fn (`KB改键设置`), edição de efeitos e frames RGB (`灯效编辑`), armazenamento de macros e perfis, ajustes magnéticos, tela e iluminação lateral. Como esse bundle atende vários produtos e marcas, só são funcionalidades presentes no software; não estão ainda associadas a uma revisão K86 específica.

O helper contém caminhos de build como `D:\work\dj_code\dj_hid_sdk_rs\target\i686-pc-windows-msvc`, evidência de alta confiança de compilação a partir de código Rust. Strings estáticas incluem tabelas de dispositivos USB: `3151:4011` interface 2, usage page `0xFFFF`, usage `0x02`, marcado como dongle comum; `3151:4015` interface 2 com a mesma coleção; e `3151:4012` classificado como transporte BLE. O helper também contém IDs `3151:5002` e `3151:5056` na coleção vendor HID. Essas tabelas do helper não identificam sozinhas quais revisões são K86; a associação por modelo vem das fontes comunitárias listadas em `docs/01-community-compatibility.md`.

## Helper nativo e APIs observadas

Imports de `iot_driver.exe` observados com `objdump -p`:

- `ws2_32.dll`, `kernel32.dll`, `ole32.dll`, `advapi32.dll`, `secur32.dll`, `crypt32.dll`, `shell32.dll`, `pdh.dll`, `powrprof.dll`, `oleaut32.dll`, `iphlpapi.dll`, `ntdll.dll`, `user32.dll`, `version.dll`, `d3d11.dll`, `dxgi.dll`, `bcrypt.dll`, `psapi.dll` e runtimes CRT.
- APIs importadas relevantes: `DeviceIoControl`, `CreateFileW`, `ReadFile`, `WriteFile`, `NtCreateFile`, `NtDeviceIoControlFile`, `NtReadFile`, `NtWriteFile`, além de consultas de registro.
- Não foram observados imports diretos com nomes `HidD_*`, `HidP_*`, `SetupDi*` ou `WinUsb_*` na listagem de imports consultada.
- O helper usa nomenclatura interna `hid_raw` e uma tabela de coleções HID em strings, indicando acesso por biblioteca/camada de HID; ainda não se identificou a implementação de transporte nem os caminhos de chamada.

Essas observações confirmam que existe I/O nativo no helper, mas não provam que os handles sejam do teclado nem revelam protocolo, identificadores, payloads ou se o helper usa resolução dinâmica de APIs. `DeviceIoControl` pode atender vários tipos de dispositivos. O conteúdo ainda não foi decompilado nem correlacionado com o frontend.

## Assinatura, dependências e persistência

- A presença de versão/identidade de produto é evidência de metadados; o estado de assinatura digital ainda não foi consultado.
- O instalador usa plugins NSIS e inclui um desinstalador. Não foi feita instalação, portanto não se conhecem os destinos finais nem possíveis drivers/serviços.
- O `main.js` usa `app.getLoginItemSettings` / `setLoginItemSettings` para a preferência de iniciar com login e `@electron/remote` para acesso à API Electron. Isso documenta apenas preferências da aplicação.
- Ainda não há evidência suficiente sobre onde perfis são gravados nem se há armazenamento persistente no teclado.

## Limitações e próximos passos da fase

- A árvore do pacote foi listada e componentes relevantes foram extraídos para `/tmp`, mas os binários não foram executados nem instalados.
- Não foram incluídos binários proprietários no repositório.
- O REA abriu o PE principal e produziu visão geral via Ghidra 12.1.4. O helper também foi aberto, mas a visão geral excedeu 300 segundos e falhou por timeout; não se atribuem resultados de função a ele aqui.
- No helper, `inspect_pe_resources` via REA (parser PE, sem execução/disassembler) observou 11 recursos e identidade SHA-256 coincidente. Uma busca de strings no alvo via Ghidra também atingiu timeout de 300 segundos. Ainda não existe pseudocódigo REA confiável do helper.
- Para concluir o mapa de arquitetura, falta analisar como o frontend inicia/controla `iot_driver.exe`, que argumentos e canais usa, e o papel do executável principal extraído. Essas respostas pertencem à análise estática focalizada da fase seguinte.
