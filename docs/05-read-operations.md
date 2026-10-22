# Ciclo 5 — consultas yc500

## Evidência e limites

Fonte principal: [sharkfin `docs/PROTOCOL.md`](https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md), protocolo versionado no repositório consultado em 2026-10-22. Os campos marcados [HW] são testes publicados pelo projeto sharkfin, não testes desta unidade. O registro local `docs/03-identification-hardware.jsonl` comprova somente `0x8F` → ID 1168. O catálogo associa 1168 / `3151:4015` ao K86 yc500; portanto a família é evidência catalogada, validada pelo ID local e ainda não uma medição independente do firmware.

Relatórios de protocolo têm 64 bytes, opcode no byte 0, Report ID HID 0 acrescentado pelo transporte. Consultas usam checksum Bit7 (`0xFF - (sum(bytes 0..6) & 0xFF)`, byte 7); `0x87` e `0x88` usam Bit8 (bytes 0..7, checksum no byte 8). A documentação não estabelece validação de checksum nas respostas. A biblioteca, portanto, valida o checksum que codifica para envio e não rejeita respostas com base em checksum presumido.

| Opcode | Consulta e entrada | Resposta / decoder | Evidência |
|---|---|---|---|
| `0x80` | Revisão, sem payload | u16: `(reply[2] << 8) | reply[1]` | [HW] |
| `0x85` | Perfil ativo, sem payload | `reply[1]`, índice zero baseado | [HW]. Não seleciona perfil por parâmetro |
| `0x86` | Opções, sem payload | flags em byte 2, Fn matrix em 3, power-save em 4 | [HW], yc500; não inferir significado/estado além dos campos documentados |
| `0x87` | Parâmetros LED, sem payload, Bit8 | mode, speed, brightness, flags/opções, RGB nos bytes 1..7 | [HW] |
| `0x88` | Parâmetros LED lateral, sem payload, Bit8 | Mesmo layout de resposta descrito para LED | Opcode/layout comuns documentados; presença no K86-1168 não foi confirmada |
| `0x89` | Keymap base `[profile, page]`, page 0..7 | Página bruta de 64 bytes, sem exigir eco | [HW] |
| `0x8B` | Macro `[slot, page]`, slot 0..49, page 0..3 | Página bruta de 64 bytes | [HW] |
| `0x8C` | Userpic, sem payload | Relatório bruto; fonte alerta que readback é estável e pode não refletir gravações | [HW], dado potencialmente não representativo |
| `0x90` | Camada Fn `[profile, page]`, page 0..7 | Página bruta de 64 bytes | Forma de consulta documentada para yc500; publicada como [HW] para mapas yc500 |
| `0x91` | Debounce, sem payload | valor em byte 2; faixa documentada 1..10 | [HW] |
| `0x92` | Timers, sem payload | quatro u16 LE em bytes 1..8: BT sleep, 2.4G sleep, BT deep sleep, 2.4G deep sleep | [HW] |
| `0x97` | Auto-OS, sem payload | booleano: `reply[1] == 1` | GET documentado; usado no sweep [HW] |

O código implementa as operações acima como `Query`/decoders sem I/O. As páginas `0x89` e `0x90` aceitam índice de perfil de um byte e página 0..7; sharkfin não especifica aqui uma contagem universal de perfis. `0x85` retorna o perfil ativo — não é leitura de um perfil solicitado. Valores decodificados de revisões/timers/flags não têm faixas universalmente estabelecidas, então não são falsamente limitados. Debounce fora de 1..10 é valor inesperado e deve ser reportado ao chamador para interpretação, não usado para qualquer escrita.

Os testes usam fixtures sintéticas e explícitas, com conteúdo de exemplo apenas para verificar layout. Não são respostas do teclado. A fixture física real permanece exclusivamente a resposta do identify em `docs/03-identification-hardware.jsonl`.

## Guarda de acesso físico

`K86Client.read_yc500(query, allow_hardware=True)` exige opt-in explícito, abre o dispositivo suportado, envia uma consulta `0x8F` na mesma conexão, exige ID 1168 e então transmite uma única consulta permitida. A proteção também existe no `HidConnection`: GETs de configuração exigem `allow_configuration=True` e ID 1168 previamente validado naquele handle. Família diferente, ID divergente e consulta sem opt-in são recusados. Não há retry. Roundtrips e fechamento no mesmo handle são serializados. CLI atual ainda não expõe execução dessas consultas; `--simulate` decodifica evidência armazenada sem abrir HID.

Não foram implementados SETs, rotinas de inicialização ou consultas automáticas.
