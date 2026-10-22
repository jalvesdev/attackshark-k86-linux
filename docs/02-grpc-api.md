# API gRPC-Web entre a interface e `iot_driver.exe`

## Fronteira e arquivos

O bundle extraído em `/tmp/attack-shark-inventory/resources/app/dist/js/index.b078bf5f.js` contém o cliente protobuf-ts e aponta para `http://127.0.0.1:3814`. O processo principal/front-end chama o helper por gRPC-Web. Isso é protocolo local app→helper; os campos `msg` podem carregar bytes que o helper transforma em operações HID, mas uma chamada RPC não é, por si, um comando USB.

Não foram encontrados `.proto` no pacote extraído. O bundle contém código protobuf-ts gerado inline (descritores de mensagem, campos, tags e codecs), e o helper contém strings de caminho de build `src/grpc_server/mod.rs` e `.../out/driver.rs`, indicando que a implementação Rust usa código gerado. Não foi localizado fonte `.proto` original nem descriptor set recuperável no payload examinado. O código gerado permite reconstruir os schemas observáveis, não os comentários ou opções originais ausentes.

## Serviço e métodos

Serviço protobuf `driver.DriverGrpc`. Métodos observados no descriptor `Ip` dentro do bundle:

| Método | Forma | Entrada → saída | Papel aparente |
|---|---|---|---|
| `watchDevList` | streaming do servidor | vazio → `DeviceList` | lista/eventos de dispositivos |
| `watchVender` | streaming do servidor | vazio → `VenderList` | estado/eventos do fornecedor/dispositivo |
| `watchSystemInfo` | streaming do servidor | vazio → `SystemInfo` | telemetria do host |
| `sendMsg` | unary | `SendMsg` → `Response` | envia mensagem com checksum/tipo |
| `readMsg` | unary | `ReadMsg` → `ResRead` | lê mensagem normal |
| `sendRawFeature` | unary | `SendMsg` → `Response` | envia Feature Report cru |
| `readRawFeature` | unary | `ReadMsg` → `ResRead` | lê Feature Report cru |
| `setLightType` | unary | `SetLight` → resposta vazia | seleciona tipo de efeito/luz no helper |
| `upgradeOTAGATT` | streaming do servidor | `OTARequest` → `OTAResponse` | atualização OTA sobre GATT; não usada/investigada aqui |
| `muteMicrophone`, `toggleMicrophoneMute`, `getMicrophoneMute` | unary | tipos auxiliares | funções genéricas de outro produto |
| `changeWirelessLoopStatus` | unary | `WirelessLoopStatus` → vazio | trava/destrava relay wireless |
| `insertDb`, `deleteItemFromDb`, `getItemFromDb`, `getAllKeysFromDb`, `getAllValuesFromDb` | unary | mensagens DB | armazenamento local do helper |
| `cleanDev` | unary | `ReadMsg` → `Response` | fecha/limpa dispositivo pelo caminho |
| `getVersion`, `getWeather` | unary | vazio/consulta → respostas próprias | metadados/serviço auxiliar |

Grafias `Vender` e `disk_spce_available` são as grafias observadas no schema, possivelmente erros do original.

## Mensagens e campos protobuf observados

- `SendMsg`: `1 devicePath:string`, `2 msg:bytes`, `3 checkSumType:enum`, `4 dangleDevType:enum`.
- `ReadMsg`: `1 devicePath:string`.
- `Response`: `1 err:string`.
- `ResRead`: `1 err:string`, `2 msg:bytes`.
- `Device`: `1 devType:enum`, `2 is24:bool`, `3 path:string`, `4 id:int32`, `5 battery:uint32`, `6 isOnline:bool`, `7 vid:uint32`, `8 pid:uint32`.
- `DJDev`: oneof `1 dev:Device` ou `2 dangleCommonDev:DangleCommonDev`; `DeviceList` contém repetidos `devList` (tag 1) e `type` enum (tag 2).
- `SetLight`: `1 devicePath:string`, `2 lightType:enum`, `3 screen_id:uint32`, `4 dangleDevType:enum`.
- `WirelessLoopStatus`: `1 lock:bool`.
- `SystemInfo`: tags 1–4 `uint64` para disco/rede, tag 5 `float` temperatura, tags 6–7 `uint64` memória e tag 8 `float` CPU.

O código protobuf-ts define leitura e escrita binária com wire types padrão (varint, length-delimited, fixed32/fixed64), preservação opcional de campos desconhecidos e codecs de enum. A pilha gRPC-Web define `Content-Type: application/grpc-web+proto` (ou `application/grpc-web-text`), `X-Grpc-Web: 1`, timeout e frames de resposta. No wrapper de UI, `sendMsg` preenche `msg`, caminho, checksum e tipo de dispositivo; sucesso é `response.err === ""`, caso contrário rejeita com erro. `readMsg`/`readRawFeature` retornam `response.msg` se o erro estiver vazio; exceções são propagadas ou, em certos métodos wrappers, convertidas em `false`/undefined. Os wrappers distinguem uso do SDK e fallback direto de Feature Report.

## Relação com configuração do teclado

O frontend contém ações genéricas para keymap (camada base/Fn), perfis, macros, efeitos/RGB e configurações, além de classes comuns que constroem `Uint8Array` de comandos. Essas classes chamam `sendMsg` ou `sendRawFeature`; a camada gRPC transporta uma mensagem protobuf até o helper. A camada USB, checksum final, seleção da interface HID e significado dos bytes residem no helper e/ou no protocolo do teclado. Os endpoints `sendMsg` e `sendRawFeature` são portanto APIs de transporte, não nomes de comandos de teclado. A enumeração `watchDevList` permite à UI obter caminhos/VID/PID antes de selecionar o dispositivo.

Arquivos/funções de referência no bundle minificado: descriptor `driver.DriverGrpc` (`new w3(...)`), codecs `SendMsg`, `ReadMsg`, `Response`, `ResRead`, `Device`, `DeviceList`, `SetLight`; cliente `kR` com métodos homônimos; wrappers em namespace `Me` com `client` gRPC e funções `sendMsg`, `sendRawMsg`, `readMsg`, `readRawMsg`, `cleanDevByPath`. O bundle minificado não tem source map ou nomes originais recuperáveis nesta extração.
