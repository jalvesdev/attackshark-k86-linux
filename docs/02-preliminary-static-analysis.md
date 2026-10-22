# Análise estática preliminar

Data: 2026-10-21. Esta nota registra evidências suficientes para orientar a próxima fase; não é um mapa completo de funções nem uma especificação de protocolo.

## Alvos e hashes

| Componente | SHA-256 | Observação |
|---|---|---|
| Instalador `ATTACK SHARK K86 SOFT.exe` | `3ee70880c8b5adcd469a0e3ebefa7e280a22fa23ff74e369955511a2c58e04a2` | Original preservado no diretório do projeto |
| App Electron `Attack Shark Driver v4.exe` | `9a8a69394f94a23dc787662129852742ddd487d651c3f65dabeffe56439b2814` | Extraído somente em `/tmp` |
| Helper `resources/app/iot_driver.exe` | `ef43fd46fe8f9908cd71e15032b76390ee79bd67de78683facc2127eafe514b1` | Extraído somente em `/tmp` |

## Evidências observadas

1. **Formato e contêiner:** `file`, 7-Zip e REA identificam o arquivo externo como PE32 x86; 7-Zip identifica NSIS-3 Unicode e o arquivo interno 7z. Nenhum binário foi executado.
2. **Tecnologia:** `package.json` declara Electron/CommonJS, React 18.2 e dependências gRPC-Web/protobuf. `dist-electron/main.js` administra janela, tray e preferências da aplicação. Strings do helper carregam paths `dj_hid_sdk_rs` e tabela HID, indicando compilação Rust.
3. **Fronteira entre aplicação e helper:** o JavaScript compilado declara cliente gRPC-Web no endereço loopback `http://127.0.0.1:3814`, chamadas protobuf para mensagens normais e raw Feature Reports, leitura e limpeza de dispositivos. O frontend escolhe uma versão de `iot_driver` na pasta de dados do usuário e copia/abre o binário empacotado. Isso separa chamadas locais da UI das operações nativas.
4. **Interface HID de destino:** strings compiladas incluem registros para VID `0x3151`, PIDs `0x4011`, `0x4015`, `0x4012`, `0x5002` e `0x5056`, com coleções HID vendor e números de interface. A tabela identifica tipos de conexão/coleção, mas não fornece associação completa entre todas as revisões e operações.
5. **APIs Windows:** imports do helper incluem `CreateFileW`, `DeviceIoControl`, `ReadFile`, `WriteFile`, `NtCreateFile`, `NtDeviceIoControlFile`, `NtReadFile` e `NtWriteFile`; não foram observados imports nomeados `HidD_*`, `SetupDi*` ou `WinUsb_*`. O uso de biblioteca HID em Rust permanece inferido a partir de strings e metadados.
6. **Frontend presente no pacote:** há estados de remapeamento/layer Fn, edição de iluminação/frame RGB, macros e armazenamento de perfis, além de controles genéricos de tela, iluminação lateral e recursos magnéticos. O bundle serve vários dispositivos; vínculo com o K86 exato ainda não foi estabelecido.

## REA MCP

- `open_binary` abriu o PE principal e o helper, com hashes coincidentes aos cálculos locais.
- `binary_overview` do PE principal retornou 269 procedimentos, 237 strings e imagem base `0x400000` pelo provedor Ghidra 12.1.4.
- `inspect_artifact` no instalador retornou inventário genérico sem arquivos filhos, pois a estrutura NSIS não foi reconhecida como container. A listagem segura do 7-Zip revelou o payload, preservando essa limitação da evidência.
- `binary_overview` e `search_strings` do helper excederam o timeout de 300 segundos; sem pseudocódigo ou call graph aceitos.
- `inspect_pe_resources` do helper foi concluído no parser PE do REA, enumerando 11 recursos e conferindo o SHA do alvo.
- No ciclo 2, REA abriu novamente o helper e confirmou o hash, mas uma busca literal pequena por `3151:4015` ficou sem resposta por mais de 90 segundos e foi cancelada; não surgiram xrefs, funções ou pseudocódigo. Como alternativa estática, `strings -a` confirmou `src\\dj_hid_device\\mod.rs`, `src\\grpc_server\\mod.rs`, serviço `driver.DriverGrpc`, rotas e tabela HID. Isso confirma símbolos/caminhos embutidos, não o fluxo de execução das rotinas.
- A ficha atual do sharkfin relaciona a unidade local `3151:4015` à variante K86 1168/yc500. Como o identificador interno não foi lido, essa revisão é provável. A matriz completa de revisões e a análise gRPC estão em `docs/02-device-identification.md`, `docs/02-community-protocol-analysis.md` e `docs/02-grpc-api.md`.
- `analyze_javascript_application` analisou de forma inerte, em uma extração parcial, `package.json`, `dist-electron/main.js` e o bundle UI: 2.156.675 bytes de texto, 2 arquivos JS parseados, 523.144 nós AST, 1.563 findings; identificou 1 BrowserWindow e seis operações/canais IPC do lado principal. Não houve parse failure. A árvore semântica foi truncada pelos limites de 20.000 nós por arquivo e 100.000 nós total; vários fluxos permanecem unknown. Os achados diretos de gRPC-Web e helper foram conferidos no bundle extraído, sem inferir relações que o grafo truncado não preservou.

## Limites do que se pode concluir

- Não há comandos HID, payloads, checksums, sequência de handshaking ou tamanhos de relatório do software original confirmados por análise própria.
- Os métodos `sendMsg`/`sendRawFeature` são chamadas do protocolo local app-helper, não opcodes do teclado.
- Imports do helper demonstram I/O genérico; isoladamente não demonstram qual arquivo/handle é o teclado nem como a mensagem vira um Feature Report.
- Os IDs USB do helper e os IDs de revisão descritos pelo projeto comunitário são cruzados em parte, mas requerem validação pela conexão USB com fio do equipamento presente.
- Não houve leitura do dispositivo, execução do helper, teste de hardware, escrita no teclado, firmware ou teste de protocolo.

## Próxima pergunta técnica

Localizar as rotinas do helper que (a) enumeram `hid_device_info`, (b) selecionam interface/usage e (c) implementam `readRawFeature`/`sendRawFeature`; seguir chamadas até as funções que montam/validam mensagens e comparar com o fluxo do bundle. A primeira validação física deve ser apenas identificação/leitura comprovada da revisão com fio.
