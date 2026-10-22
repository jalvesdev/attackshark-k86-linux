# ATTACK SHARK K86 para Fedora

Este projeto investiga uma implementação Linux independente para a revisão K86 que respondeu com ID interno 1168. O catálogo sharkfin relaciona `3151:4015` / ID 1168 a `yc3121` e protocolo `yc500`; isso confirma correspondência de catálogo, não uma medição independente do controlador nem suporte completo ao protocolo.

## Estado

- A identificação física `0x8F` foi confirmada; a resposta bruta está preservada em [`docs/03-identification-hardware.jsonl`](docs/03-identification-hardware.jsonl).
- A biblioteca `attackshark_k86` oferece descoberta/seletor de interface, validação de descritor, transporte Feature Report somente para uma lista permitida de GETs, codecs yc500, tratamento de falhas e logs estruturados.
- GETs de configuração exigem autorização explícita pela API e verificação do ID interno 1168 na mesma sessão. A CLI não executa essas consultas; não há envio implícito.
- A CLI executa simulação sem acesso HID por padrão quando solicitado. Não consulta o teclado ao iniciar.
- Não há interface gráfica, comandos de configuração, implementação de escrita, nem testes físicos novos neste ciclo.

## Instalação

As dependências de execução são declaradas em `pyproject.toml`; o ambiente é local ao projeto e não altera o Python global. Crie ou reutilize `.venv` e instale o próprio projeto:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

A instalação resolve `hidapi>=0.15` como dependência de execução. No Linux, a biblioteca seleciona a extensão hidraw (`hidraw`) da própria distribuição para usar o path dinâmico `/dev/hidrawN` coberto pela ACL da interface; não usa o backend libusb (`hid`) para abrir o path sysfs `BUS.PORT:CONFIG.INTERFACE`. A instalação não altera regras/permissões do sistema. Diagnóstico: [`docs/06.4-fedora-hidraw-open.md`](docs/06.4-fedora-hidraw-open.md).

## Simular a identificação

```sh
.venv/bin/python -m attackshark_k86 identify --simulate
```

O modo simulado decodifica a resposta física registrada e imprime um objeto JSON. Não abre dispositivos.

Para executar os testes automatizados:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Para abrir a CLI com o Python do ambiente virtual, use `.venv/bin/python -m attackshark_k86 identify --simulate`. Após a instalação editável, o atalho `.venv/bin/k86-hid identify --simulate` também fica disponível. A identificação física exige a opção explícita `--confirm-identify`.

## Identificação no hardware

Somente quando solicitado conscientemente pelo operador:

```sh
.venv/bin/k86-hid identify --confirm-identify --timeout 2 --log docs/identification-runs.jsonl
```

Isso envia uma única Feature Report de identificação `0x8F` à interface que passar pelos filtros VID/PID, interface, uso HID e descritor. O programa não repete a consulta em timeout nem resposta inválida. Consultas adicionais e toda escrita permanecem fora do escopo operacional atual.

## Arquitetura

- `device.py`: inventário hidapi e seleção estrita de `3151:4015`, interface 2 e coleção `FFFF:0002`.
- `protocol.py`: relatórios de 64 bytes, checksums Bit7/Bit8, allowlist de GETs, consulta de identificação e codecs/decoders yc500 sem I/O.
- `transport.py`: adaptador hidapi com backend hidraw no Linux, validação do descritor de Feature Report, envio/leitura com timeout observado, erros tipados e evento estruturado.

## Ciclo 5

Consultas documentadas e evidência: [`docs/05-read-operations.md`](docs/05-read-operations.md). Limitações de timeout: [`docs/05-timeout-strategy.md`](docs/05-timeout-strategy.md). A única consulta proposta para futura autorização física é `0x85` (perfil ativo); o plano não foi executado: [`docs/05-hardware-validation-plan.md`](docs/05-hardware-validation-plan.md). O resumo de ciclo está em [`docs/05-cycle-report.md`](docs/05-cycle-report.md).

## Ciclo 6

A suíte passou, mas a consulta física `0x85` não foi executada: este ambiente não tem hidapi nem nós `/dev/hidraw*`. O estado e a tentativa única para execução manual estão documentados em [`docs/06-cycle-report.md`](docs/06-cycle-report.md), usando [`tools/read_active_profile.py`](tools/read_active_profile.py).

## Ciclo 6.1

Instalação reproduzível no `.venv`, uso dos testes e CLI: este README. Após instalar dependências, o comando preparado para a única leitura física `0x85` é `.venv/bin/python tools/read_active_profile.py --timeout 2 --log docs/06-profile-hardware.jsonl`. Ele faz `0x8F`, exige ID 1168 e envia uma única `0x85`; não execute para simular.

Correção da seleção HID entre interfaces compostas e regressões: [`docs/06.2-interface-selection.md`](docs/06.2-interface-selection.md). A seleção continua estrita na interface 2 e não usa path hidraw fixo.

Correção 6.3: quando o hidapi Linux retorna uso `0/0` e strings vazias, a biblioteca trata esses campos como insuficientes e valida o descritor da interface selecionada no handle ou por sysfs com vínculo à mesma interface USB. Veja [`docs/06.3-hid-metadata.md`](docs/06.3-hid-metadata.md). Nenhuma consulta física adicional foi executada.

- `cli.py`: simulação com fixture real e comando explícito de identificação física.
- `tests/`: testes automatizados com backend fake; nenhum teste abre HID.

Correção de abertura no Fedora: a distribuição hidapi instalada expõe os backends `hid` (libusb) e `hidraw`; no Linux, a aplicação usa `hidraw` para que a ACL do nó concedida pela regra local seja suficiente. O seletor ainda exige VID:PID `3151:4015`, interface 2, USB e descritor esperado. A abertura/fechamento físico da interface 2 foi confirmada; veja [`docs/06.4-fedora-hidraw-open.md`](docs/06.4-fedora-hidraw-open.md).

Correção 6.5: o registro de TX/RX da consulta de perfil usa o estado da conexão HID, que é onde os eventos de transporte ficam disponíveis. O log da tentativa anterior foi preservado; a falha aconteceu depois do roundtrip `0x8F` e antes de `0x85`. Testes simulados de sucesso e timeout estão em [`tests/test_read_active_profile.py`](tests/test_read_active_profile.py); causa e comando para uma futura execução única estão em [`docs/06.5-profile-integration.md`](docs/06.5-profile-integration.md). Nenhuma consulta física foi executada nesta correção.

Ver [arquitetura e relatório do ciclo 4](docs/04-cycle-report.md) e [plano do protocolo](docs/04-hid-architecture.md).

## Licença e sharkfin

Este projeto utiliza informações factuais publicadas sobre IDs, layouts de relatório, opcodes e formatos. Não incorpora trechos de código sharkfin. O repositório não tinha uma licença global declarada, então este ciclo não atribui licença de distribuição ao conjunto do projeto. Se código GPL do sharkfin for incorporado no futuro, as obrigações GPL-3.0-or-later e os avisos de terceiros precisarão ser avaliados antes de distribuir essa versão.
