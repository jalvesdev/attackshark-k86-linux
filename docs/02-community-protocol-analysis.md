# Sharkfin: compatibilidade e protocolo comunitário

## Projeto e licença

O projeto de referência é [dniminenn/sharkfin](https://github.com/dniminenn/sharkfin), configurador de teclados ROYUAN/Attack Shark. O repositório declara **GPL-3.0-or-later**; componentes redistribuídos mantêm termos próprios no `THIRD-PARTY-NOTICES.md`. Reutilizar código do projeto deve cumprir GPL-3.0-or-later, incluindo obrigações aplicáveis à distribuição de obras derivadas; é possível usá-lo como referência sem copiar código. Não copiei arquivos do projeto para este repositório.

## Revisões K86 listadas

| Device ID interno | VID:PID com fio | Controlador | Família | Situação no catálogo |
|---:|---|---|---|---|
| 1168 | `3151:4015` | `yc3121_sg8967_3m_soc` | `yc500` | gravável, layout desenhado |
| 2730 | `3151:5002` | `yc3123_sg_sg8967_3m_1k` | `gen2` | gravável, layout desenhado |
| 4094 | `3151:5056` | `ry6602_sg_sg8967_3m_1k_1k` | `gen2` | gravável, conferência inicial do mapa necessária |

A página informa que as revisões respondem seu device ID interno e que o software seleciona a família a partir dele. Atualização do ciclo 4: a resposta física está preservada em `docs/03-identification-hardware.jsonl`; `3151:4015`, interface 2, respondeu ID 1168 (`90 04 00 00` little-endian) ao `0x8F`. A correspondência local com o registro K86-1168 está confirmada. O catálogo associa esse registro a `yc3121`/`yc500`; isso permanece informação catalogada, não medição independente do controlador/protocolo completo.

## Transporte e estruturas de protocolo

`docs/PROTOCOL.md` descreve Feature Reports HID de 64 bytes na coleção vendor-defined e separa `yc500` de `gen2`. OpCodes iguais podem ter significado, offsets ou formato diferentes entre famílias. A documentação marca evidências como `[HW]` (placa testada), `[FW]` (firmware analisado) e `[JS]` (código host do fornecedor sem execução). Sharkfin implementa apenas um subconjunto e informa que não faz flash de firmware.

Achados relevantes no protocolo documentado:

- Identidade: comando `0x8F`, resposta com ID u32 little-endian.
- Formato geral: report HID Feature de 64 bytes, ID de relatório 0; respostas GET normalmente repetem o opcode no byte 0, enquanto GETs bulk de keymap/Fn/macro/userpic devolvem páginas brutas. Checksum Bit7: `0xFF - (sum & 0xFF)` sobre bytes 0..6, colocado no byte 7; Bit8 cobre bytes 0..7 e fica no byte 8 para LED/SLED params. Algumas transferências de dados não têm checksum.
- Mapa: 128 slots por camada, 4 bytes por slot (512 bytes); leitura em oito páginas brutas de 64 bytes. Para yc500, GET base `0x89 [profile,page]` e Fn `0x90 [profile,page]`; em gen2, base `0x8A [profile,0xFF,page,os]`, enquanto a forma Fn também muda. Não reaproveitar a forma de um protocolo no outro.
- Perfis: três perfis declarados na ficha K86; seleção e consulta usam pares de opcodes distintos por família.
- Configurações documentadas incluem keymap base/Fn, macros, perfil, iluminação, debounce e timers de suspensão. As diferenças entre famílias são explícitas; por exemplo, perfil yc500 usa `0x05/0x85` e gen2 `0x04/0x84`; reset também difere.
- Macros: 50 slots × 256 bytes. Escrita yc500 `0x16` e gen2 `0x0B`, um report por página de 56 bytes com slot/página/comprimento/flag final.
- RGB: catálogo do K86 anuncia 18 efeitos, cores, velocidade/brilho e cor por tecla. Detalhes de cada transferência estão no código do projeto e dependem da família.
- Variantes: knob e iluminação de borda são associados apenas aos IDs 2730 e 4094; o display tem suporte de desenho informado para 1168 e 2730. O catálogo avisa que slot físico pode divergir entre placas e exige validação inicial do mapa.
- Sem fio: receptor 2,4 GHz pode ou não retransmitir o canal de configuração; Bluetooth não fornece canal de configuração. A página recomenda cabo para operações de escrita.

## Código e funções de referência

As referências abaixo foram consultadas no commit `b36c7900e768b8bfddac296516e9b8a983698087`:

- `docs/BOARDS.md`, linha do K86 1168: registro `3151:4015`, família `yc500`, writable; o mesmo arquivo distingue as linhas K86 2730 e 4094. `app/src-tauri/src/registry.rs` alimenta o catálogo de `DeviceSpec`.
- `app/src-tauri/src/hid.rs`: `discover()` filtra coleções ROYUAN e constrói `DiscoveredDevice`; `Transport::open()` abre um path hidapi; `raw_send_blocking()`/`raw_read_blocking()` executam Feature Reports 64 bytes e adicionam/toleram o byte de report ID; `identify()` delega a `Wire::identify`; `roundtrip()` e `read_raw_page()` são wrappers da conversa de protocolo. `has_settings_report()` valida report descriptor para interfaces específicas. O arquivo marca a licença SPDX GPL-3.0-or-later.
- `app/src-tauri/src/wire.rs`: trait `Wire` implementa `roundtrip`, `read_raw_page`, `try_identify` e `identify`; também contém seleção/liberação de relay do receptor. Writes são espaçados em 12 ms; esta é implementação do sharkfin, não confirmação independente para a unidade local.
- `app/src-tauri/src/derive.rs`: `detect_family()` distingue família por respostas de leitura a `0x89`, `0x8A`, `0x91` e `0x92`; casos ambíguos retornam unknown. `derive_spec()` cria registro derivado com recursos limitados.
- `app/src-tauri/src/ops.rs`: `need()` bloqueia comandos sem família conhecida; `key_write_packet()` e `write_layer_bulk()` constroem operações de escrita. Referenciados para compreender a arquitetura, não para executá-los.
- `app/src-tauri/src/protocol/gen2.rs`: `keymatrix_read_payload()`, `fn_read_payload()`, `set_key_packet()`, `set_fn_key_packet()` e `bulk_keymatrix_packets()` mostram que gen2 tem payload próprio. Os módulos `app/src-tauri/src/protocol/yc500.rs` e `cmd.rs` são pares de família/opcodes conforme a árvore do protocolo e `docs/PROTOCOL.md`.
- `docs/PROTOCOL.md`: evidências anotadas por fonte `[HW]`, `[FW]`, `[JS]`; descreve diferenças de comandos, checksum e payload. `LICENSE` e `THIRD-PARTY-NOTICES.md` controlam reaproveitamento/distribuição.

Esses nomes e descrições são evidência direta do código público sharkfin no commit indicado. Os testes/provas anotados no projeto comunitário não são validação da unidade local. Para reutilizar código, fixar o commit revisado e cumprir GPL-3.0-or-later e avisos de terceiros.

Referências diretas e fixadas: [`hid.rs`](https://github.com/dniminenn/sharkfin/blob/b36c7900e768b8bfddac296516e9b8a983698087/app/src-tauri/src/hid.rs), [`wire.rs`](https://github.com/dniminenn/sharkfin/blob/b36c7900e768b8bfddac296516e9b8a983698087/app/src-tauri/src/wire.rs), [`derive.rs`](https://github.com/dniminenn/sharkfin/blob/b36c7900e768b8bfddac296516e9b8a983698087/app/src-tauri/src/derive.rs), [`ops.rs`](https://github.com/dniminenn/sharkfin/blob/b36c7900e768b8bfddac296516e9b8a983698087/app/src-tauri/src/ops.rs), [`gen2.rs`](https://github.com/dniminenn/sharkfin/blob/b36c7900e768b8bfddac296516e9b8a983698087/app/src-tauri/src/protocol/gen2.rs), [`BOARDS.md`](https://github.com/dniminenn/sharkfin/blob/b36c7900e768b8bfddac296516e9b8a983698087/docs/BOARDS.md), [`PROTOCOL.md`](https://github.com/dniminenn/sharkfin/blob/b36c7900e768b8bfddac296516e9b8a983698087/docs/PROTOCOL.md), [`LICENSE`](https://github.com/dniminenn/sharkfin/blob/b36c7900e768b8bfddac296516e9b8a983698087/LICENSE).

## Avaliação de reaproveitamento

Para a unidade observada, o caminho provável seria aproveitar a seleção de dispositivo 1168 e a família yc500. Isso é evidência de compatibilidade por VID:PID/catalogação, não confirmação de que o dispositivo local responda nem de que todas as funções funcionem. Antes de adaptar código, deve-se identificar o device ID lido do teclado, revisar no commit escolhido as funções de abertura HID, checksum e codecs yc500, verificar a licença e depois criar testes de parser sem hardware. Não enviar comandos de escrita nesta fase.

Fontes consultadas: [repositório sharkfin e licença](https://github.com/dniminenn/sharkfin), [LICENSE](https://github.com/dniminenn/sharkfin/blob/master/LICENSE), [docs/PROTOCOL.md](https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md), [ficha K86 com tabela de revisões](https://getsharkfin.com/boards/attack-shark-k86).
