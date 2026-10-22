# Ciclo 3 — protocolo de identificação

> Atualização ciclo 4: uma resposta física ao `0x8F` está preservada em `docs/03-identification-hardware.jsonl`, confirmando o ID interno 1168 e a correspondência K86-1168. A informação `yc3121`/`yc500` continua sendo do catálogo.

## Referência sharkfin

Referência consultada: [sharkfin `docs/PROTOCOL.md`](https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md), [wire.rs](https://github.com/dniminenn/sharkfin/blob/master/app/src-tauri/src/wire.rs), [hid.rs](https://github.com/dniminenn/sharkfin/blob/master/app/src-tauri/src/hid.rs) e [protocol/cmd.rs](https://github.com/dniminenn/sharkfin/blob/master/app/src-tauri/src/protocol/cmd.rs). O projeto lista o USB `3151:4015` para a revisão K86 device ID 1168, protocolo `yc500`; isso é associação de catálogo e ainda não confirma a unidade física.

## Consulta

| Campo | Valor documentado |
|---|---|
| Coleção | Interface 2; página de uso `0xFFFF`, uso `0x02` |
| Relatório | Feature Report, ID 0, 64 bytes em cada direção |
| Opcode | `0x8F` (`GET_USB_VERSION` / identify), sem payload |
| Report de 64 bytes | `8F 00 00 00 00 00 00 70`, seguido de 56 bytes zero |
| Transação Linux | `HIDIOCSFEATURE(65)` com byte inicial de report ID zero, seguido de `HIDIOCGFEATURE(65)` para ler a resposta |
| Resposta | Byte 0 ecoa `0x8F`; bytes 1–4 contêm o device ID como `u32` little-endian |
| Identificador catalogado | 1168 decimal = `0x00000490`; bytes esperados `90 04 00 00` |

O checksum Bit7 é `0xFF - (sum(bytes 0..6) & 0xFF)`, no byte 7. Para o pacote de identify, resulta em `0x70`. O byte inicial zero adicional entregue à API hidraw/hidapi representa o report ID; não faz parte dos 64 bytes de payload do protocolo.

## É somente leitura?

O sharkfin documenta `0x8F` como handshake de identificação, válido em todas as famílias, e marca a troca/correspondência de leitura como `[HW]`. A implementação de `Wire::try_identify` constrói um pacote com opcode `GET_USB_VERSION`, payload vazio e checksum Bit7; `roundtrip_packet` envia o pacote e lê respostas até encontrar o opcode ecoado. A documentação não associa esse comando a mudança de perfil, mapa ou configuração, e o comando não está na faixa de comandos SET da tabela. Portanto, trata-se de uma **consulta lógica sem alteração de estado documentada**.

Essa conclusão não torna a operação uma leitura passiva do barramento: `raw_send_blocking` chama `send_feature_report`, isto é, envia um Feature Report ao dispositivo. A revisão exata do firmware local não foi analisada; um firmware divergente ou defeituoso ainda pode reagir de forma inesperada. Há risco adicional de ausência de resposta ou stall do endpoint de controle; o próprio sharkfin documenta stalls sob certas condições de transporte e necessidade de desconectar/reconectar. Não há base para afirmar risco zero.

## Ferramenta e proteção

`tools/identify_k86.py` implementa somente identificação, sem comandos de configuração. Valida VID:PID pelo caminho sysfs, exige interface 2, usa buffers de 65 bytes para a camada hidraw (ID + payload), limita a espera do ioctl e salva transação e resposta como JSON Lines. O padrão é simulação. O modo hardware exige literalmente `--authorize-send IDENTIFY-3151:4015`; não foi invocado nesta etapa. A CLI rejeita respostas com opcode/tamanho inesperados e não classifica IDs desconhecidos como K86.

Resultado simulado registrado durante este ciclo: a resposta documentada `8F 90 04 00 00 …` foi interpretada como ID 1168 e classificada como correspondência de catálogo `K86-1168-catalog-match`. Este resultado é um teste do parser, não uma leitura da unidade.

## Revisão anterior ao envio autorizado

Na revalidação de 2026-10-22, o código sharkfin continua montando `roundtrip(GET_USB_VERSION=0x8F, payload vazio, Checksum::Bit7)`. `roundtrip_packet` transmite uma única vez e depois lê até cinco vezes em caso de resposta sem opcode coincidente; a função de alto nível `try_identify` pode repetir a consulta até três vezes. Esta CLI limita a tentativa autorizada a uma única chamada HIDIOCSFEATURE seguida de uma chamada HIDIOCGFEATURE, sem repetição após erro ou resposta inesperada.

Em `hid.rs`, o payload de protocolo é colocado nos bytes 1..64 do buffer hidapi de 65 bytes, deixando byte 0 como Report ID zero. `send_feature_report` envia esses 65 bytes; `get_feature_report` também usa 65 bytes e remove o byte de Report ID da resposta quando apropriado. Nesta CLI Linux, os ioctl hidraw correspondentes usam tamanho 65, report ID zero e 64 bytes de payload. O pacote calculado é `8f00000000000070` seguido por 56 zeros: opcode em byte 0 e checksum `0x70` no byte 7. O parser exige 64 bytes, opcode `0x8F` e interpreta bytes 1..4 como u32 little-endian.

A execução real ficou bloqueada antes do primeiro ioctl de envio: `/dev/hidraw11` não existe na visão deste processo. A autorização fornecida não foi consumida por uma tentativa parcial; não houve envio nem resposta física. O procedimento deve ser executado uma única vez no host Fedora, conforme `docs/03-hardware-test-plan.md`.
