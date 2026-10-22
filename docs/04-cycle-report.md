# ATTACK SHARK K86 — Relatório do ciclo 4

Data: 2026-10-22

## Resultado da identificação

A identificação física foi confirmada. O log JSONL preexistente foi preservado em `docs/03-identification-hardware.jsonl`. A resposta recebida foi:

```text
8f900400000000700000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000
```

O opcode ecoado é `0x8F`. Bytes 1–4 são `90 04 00 00`, interpretados como `u32` little-endian `0x00000490` = **1168**. O byte 7 (`0x70`) é retido exatamente como recebido; a resposta não é submetida a regra de checksum não documentada. VID/PID `3151:4015`, interface 2, Report ID 0 e payload de 64 bytes também correspondem aos metadados do registro. Isso confirma a correspondência com K86-1168 no catálogo sharkfin.

O catálogo associa ID 1168 ao controlador `yc3121_sg8967_3m_soc` e à família `yc500`. Não medimos diretamente o controlador nem executamos outros comandos. **Comandos de configuração continuam sem teste** e não foram adicionados à biblioteca.

## Entregáveis

- Biblioteca modular `attackshark_k86`: descoberta, seleção estrita por VID/PID/interface/coleção, validação de descritor, conexão/fechamento, transporte Feature Report, codecs de consulta e logs estruturados.
- Identificação `0x8F` migrada e baseada na fixture física preservada.
- Codificadores/decodificadores simulados para consultas yc500 documentadas. Nenhuma dessas consultas adicionais foi enviada ao hardware.
- CLI `python3 -m attackshark_k86 identify --simulate` e confirmação explícita `--confirm-identify` para qualquer chamada física futura. A CLI não consulta no startup.
- Testes automatizados sem HID físico. Não foi feito teste físico adicional.
- `README.md` com instalação opcional do hidapi, testes e uso.

## Testes

Executado:

```sh
python3 -m unittest discover -s tests -v
```

Os testes cobrem seleção de dispositivo/interface/descritor/barramento, bytes exatos do `0x8F`, decodificação da resposta real como 1168, checksum Bit7/Bit8, consultas e decoders yc500, recusa de SET, resposta inválida/curta, timeout, permissão negada, desconexão, fechamento e deadline. Resultado final: **17 testes aprovados**.

## Licenciamento

O sharkfin declara GPL-3.0-or-later. Este ciclo reutilizou fatos do protocolo e dados do catálogo; não copiou código-fonte do sharkfin. O repositório original não tinha licença global informada, portanto este ciclo não declara licença de distribuição para o conjunto do projeto. A dependência opcional hidapi mantém seus próprios termos. Incorporar código GPL futuramente exige análise de licença, avisos e obrigações de distribuição antes da publicação.

## Limitações e próximo ciclo

- Só `0x8F` teve resposta real observada; as outras operações são apenas codecs documentais/simulados.
- Família/controlador seguem associação do catálogo para o ID 1168, sem medição independente.
- hidapi não fornece timeout/cancelamento portátil para todo `get_feature_report`; a deadline detecta demora após retorno. Timeout do backend é mapeado, sem retry.
- Próximo ciclo: validar em simulação os payloads/decoders com fixtures documentadas e, com autorização separada, escolher uma única consulta GET não modificadora para comparação no hardware. Permanecer sem interface gráfica e sem escrita até esse processo.
