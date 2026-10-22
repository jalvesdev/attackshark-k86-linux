# Análise focalizada de `iot_driver.exe`

## Identidade e método

Alvo preservado fora do Git: `/tmp/attack-shark-inventory/resources/app/iot_driver.exe`, PE32 x86, SHA-256 `ef43fd46fe8f9908cd71e15032b76390ee79bd67de78683facc2127eafe514b1`. Não foi executado. Imports observados no inventário anterior incluem `CreateFileW`, `ReadFile`, `WriteFile`, `DeviceIoControl`, `NtCreateFile`, `NtDeviceIoControlFile`, `NtReadFile` e `NtWriteFile`.

## REA MCP

REA abriu o binário neste ciclo e confirmou o caminho, arquitetura e hash. Uma consulta literal pequena em `3151:4015` permaneceu sem resposta por mais de 90 segundos, após histórico anterior de timeout em `binary_overview` e `search_strings` acima de 300 segundos. A chamada foi cancelada antes de repetir uma análise global. Portanto, não há evidência REA utilizável de procedimento, xref, pseudocódigo, chamadores ou endereços. A indisponibilidade é do provedor/consulta do REA, não falta de strings no arquivo.

## Evidência estática alternativa

`strings -a` sobre o PE confirma os nomes dos fontes de build `src\\dj_hid_device\\mod.rs` e `src\\grpc_server\\mod.rs`, paths de dependências Rust/Tonic, o nome do serviço `driver.DriverGrpc`, nomes de rotas RPC e caminho do `out/driver.rs` gerado. A tabela embutida contém:

- `3151:4011`, interface 2, usage page `0xFFFF`, usage `0x02`, `dongle_common=true`;
- `3151:4015`, interface 2, mesma coleção vendor-defined;
- `3151:5002` e `3151:5056`, também interface 2 / usage vendor-defined;
- `3151:4012` listado como BLE (`usage page 0xFF66`, usage `0x202`), além de diversos IDs de outros produtos.

Também aparecem strings da biblioteca hidapi: `hid_enumerate`, `hid_open_path`, `hid_get_feature_report` e `hid_send_feature_report`, além de tipos de erro e `OpenHidDeviceWithDeviceInfoError`. Isso fortalece a conclusão de que a camada nativa enumera caminhos e usa Feature Reports via hidapi. Não revela ainda qual função encapsula cada chamada, os tamanhos usados em runtime ou seus callers. Arquivos/funções de origem que podem ser buscados quando REA estiver operacional: `src/dj_hid_device/dj_hid/hid_normal.rs`, `src/dj_hid_device/dj_hid/mod.rs`, `src/dj_hid_device/mod.rs`, `src/grpc_server/mod.rs`.

O executável carrega também uma segunda tabela de IDs para operações distintas (por exemplo, interface `-1`, usage page `0xFF01`, e entradas de bootloader); não se deve inferir que cada PID dessa tabela seja um K86.

Esses caminhos e símbolos são strings do binário e ajudam a localizar módulos Rust, mas não revelam sozinhos a lógica executável. A tabela mostra seleção/compatibilidade HID, não associa cada endpoint RPC a um envio específico.

## Resultado por tópico solicitado

| Tópico | Conclusão com evidência atual |
|---|---|
| Strings VID/PID | Confirmadas por strings ASCII e tabela incorporada; ver acima e `docs/01-binary-inventory.md`. |
| Xrefs às strings | Não obtidos; REA não respondeu à consulta direcionada. |
| Rotina de abertura | Strings `hid_enumerate`, `hid_open_path` e `OpenHidDeviceWithDeviceInfoError` identificam a biblioteca/ação; nomes dos módulos-fonte embutidos disponíveis acima. Corpo, callers e endereço não identificados. |
| Read/Write/DeviceIoControl | Imports Win32 presentes e strings hidapi `hid_get_feature_report`/`hid_send_feature_report`. O caminho provável é hidapi sobre HID; não atribuo chamadas específicas a `3151:4015` sem fluxo de dados. |
| Buffer e protocolo | A UI fornece bytes protobuf em `SendMsg.msg`; o helper declara tipos/checksum e operação raw-feature. Conversão para HID e conteúdo de protocolo permanecem desconhecidos no binário original. |
| Serialização RPC | Tonic/Rust e código gerado `driver.rs` observados; os métodos e wire schemas foram recuperados da contraparte JavaScript em `docs/02-grpc-api.md`. |

Não há arquivos `.pdb`, fonte Rust, `.proto` ou descriptor set no conteúdo extraído. Próximo método útil: uma consulta REA com provider funcional e procedimento único selecionado por xref de string/import, ou ferramenta local Ghidra/rizin para mapear imports e callers. O método deve começar com abertura HID, seleção de path, `send_feature`/`get_feature` e conversão do checksum, preservando chamadas de escrita sem execução.
