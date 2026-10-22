# Ciclo 4 — arquitetura da biblioteca HID

## Limites e estado confirmado

O log [`03-identification-hardware.jsonl`](03-identification-hardware.jsonl) contém uma consulta física bem-sucedida ao teclado USB `3151:4015`, interface 2, Report ID 0. A resposta bruta é preservada sem reescrita. Os bytes de ID são `90 04 00 00` (resposta posições 1–4), que em little-endian valem `0x00000490` = 1168. O byte 7 da resposta física é `0x70`, ecoando o checksum enviado; não se valida checksum em resposta porque o protocolo não documenta essa regra.

O catálogo sharkfin associa 1168 à revisão K86, controlador `yc3121_sg8967_3m_soc` e protocolo `yc500`. A identificação física confirma o ID interno e a correspondência de catálogo; controlador e família são dados catalogados, não medições independentes da placa. Nenhuma configuração foi testada.

## Módulos

- `attackshark_k86.device`: `DeviceInfo`, `DeviceSelector`, enumeração hidapi, seleção única por VID/PID `3151:4015`, interface 2, USB quando reportado, usage page `0xFFFF` e usage `0x02`.
- `attackshark_k86.protocol`: pacotes Feature Report de 64 bytes, Report ID 0 à parte, checksums Bit7/Bit8, validação de relatório HID, allowlist de GETs e decodificação de respostas yc500.
- `attackshark_k86.transport`: adaptador para o binding Python do hidapi, abertura pelo path dinâmico enumerado, validação do descritor antes do envio, uma troca por chamada, erros tipados, fechamento e logs JSON estruturados. Em Linux, usa a extensão `hidraw` da distribuição `hidapi` (não a extensão `hid` compilada com libusb), porque a permissão concedida ao nó `/dev/hidrawN` não implica acesso USBFS. Se o binding não expõe `get_report_descriptor`, Linux resolve o path enumerado por sysfs e valida VID:PID, interface USB e `HID_ID` antes de ler `report_descriptor`; veja [`06.3-hid-metadata.md`](06.3-hid-metadata.md). Essa leitura local de metadados não envia Feature Report.
- `attackshark_k86.cli`: simulação sem HID usando o log real como fixture; consulta física somente com subcomando e confirmação explícita `--confirm-identify`.

O hidapi foi escolhido por abstrair hidraw e por implementar os Feature Reports que o sharkfin também usa no desktop. No Fedora, o backend pode retornar `usage_page=0`, `usage=0` e strings vazias; esses valores são inconclusivos e não autorizam abertura por si sós. A biblioteca exige o descritor `FFFF:0002` e o Feature Report de 64 bytes com Report ID 0 obtido do handle ou, se ausente no binding, de sysfs verificado para o mesmo VID:PID/interface e nó HID. O código usa o path retornado na enumeração e nunca assume um número `hidrawN` fixo. Cada handle serializa as trocas para evitar sobreposição de chamadas; fechamento também espera a chamada ativa terminar e não é cancelamento. A dependência `hidapi>=0.15` também fornece a extensão `hidraw` usada para enumerar/abrir diretamente o nó autorizado no Linux. Ver causa e detalhes em [`06.3-hid-metadata.md`](06.3-hid-metadata.md) e [`06.4-fedora-hidraw-open.md`](06.4-fedora-hidraw-open.md).

## Proteções de transporte

O seletor recusa PID/interface/coleção diferentes, seleciona a interface 2 antes de validar uso e barramento, e requer exatamente uma correspondência. Coleções HID extras no mesmo VID:PID não desviam a seleção. Antes de transmitir, o descritor deve declarar Feature Report ID 0 com 64 bytes. A codificação só aceita a allowlist de GETs yc500; opcodes SET conhecidos ou desconhecidos falham com `UnauthorizedWrite`. Respostas devem ter 64 bytes (com ou sem o byte de Report ID), opcode esperado para GETs com eco e conteúdo suficiente para os decoders. A chamada não tem retry. Detalhe da causa e da regressão: [`06.2-interface-selection.md`](06.2-interface-selection.md).

Timeout é uma deadline observada no cliente e erros de timeout fornecidos pelo backend são mapeados. Limitação: o hidapi Python não oferece parâmetro portátil de timeout/cancelamento para `get_feature_report`; se um backend permanecer bloqueado dentro de um ioctl, a deadline só pode ser reconhecida quando a chamada retornar. Não se usa thread abandonada nem uma segunda transação para contornar isso. Desconexão, permissão negada, resposta curta/malformada e erro de transporte são exceções distintas. Estratégia detalhada e opção de processo isolado para GUI futura: [`05-timeout-strategy.md`](05-timeout-strategy.md).

## Consultas yc500 preparadas (sem envio neste ciclo)

| Consulta | Payload de pedido | Resposta decodificada |
|---|---|---|
| identify `0x8F` | vazio | `u32` little-endian nos bytes 1–4 |
| revision `0x80` | vazio | `(reply[2] << 8) | reply[1]` |
| profile `0x85` | vazio | byte 1 |
| options `0x86` | vazio | bytes 2–4 (flags, Fn matrix, power save) |
| LED params `0x87` | vazio | modo, velocidade, brilho, flags/opções e RGB |
| side LED params `0x88` | vazio | mesmo formato documentado para parâmetros |
| base keymap `0x89` | `[profile, page 0..7]` | página crua de 64 bytes |
| macro `0x8B` | `[slot, page 0..3]` | página crua de 64 bytes |
| userpic `0x8C` | vazio | relatório cru; sharkfin alerta que GET estável não reflete necessariamente gravações |
| Fn map `0x90` | `[profile, page 0..7]` | página crua de 64 bytes |
| debounce `0x91` | vazio | byte 2 |
| sleep timers `0x92` | vazio | quatro `u16` little-endian em bytes 1..8 |
| auto-OS `0x97` | vazio | byte 1 igual a 1 |

As entradas `yc500_queries()` apenas codificam objetos Query. GETs de configuração exigem autorização explícita na API e confirmação do ID 1168 na mesma sessão; nenhum foi executado no teclado neste ciclo. Não há APIs de configuração/write na biblioteca. Veja [`05-read-operations.md`](05-read-operations.md) e o plano da consulta `0x85` em [`05-hardware-validation-plan.md`](05-hardware-validation-plan.md).

Disponibilidade de recursos varia por revisão: por exemplo, a presença do GET de side LED no protocolo não comprova que a revisão 1168 exponha esse recurso. Os codecs são documentação de wire format, não uma declaração de suporte funcional no K86 físico.

## Verificação

Testes ficam em `tests/` e usam backend falso e resposta real registrada; não enumeram nem abrem HID. Comando: `python3 -m unittest discover -s tests -v`. O resultado atual deve ser registrado em `docs/04-cycle-report.md`.
