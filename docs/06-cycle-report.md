# Relatório do ciclo 6 — validação física do perfil ativo

## Estado

**Teste físico não executado.** A suíte automatizada passou, mas o ambiente de execução não tem o módulo `hid`/hidapi (`ModuleNotFoundError`) e não expõe nós `/dev/hidraw*`. Portanto não foi possível enumerar o teclado, confirmar fisicamente VID:PID/interface/descritor ou abrir a interface. A execução parou antes de qualquer acesso HID. Nenhum comando foi transmitido; não houve mudança de permissão nem uso de `sudo`.

## Pré-verificação do protocolo

`python -m unittest discover -v`: **25 testes aprovados**. A consulta `0x85` foi verificada localmente: yc500, payload vazio, relatório de protocolo de 64 bytes, Bit7 checksum `0x7A` no byte 7; hidapi deve receber 65 bytes, prefixo Report ID `0x00` seguido do relatório. O pacote confere byte a byte com a documentação sharkfin sobre perfil ativo, que especifica GET sem argumento e `reply[1]` como índice atual zero baseado.

## Artefato manual preparado

[`tools/read_active_profile.py`](../tools/read_active_profile.py) abre somente a coleção suportada, valida descritor antes de transmitir, registra metadados, envia um identify `0x8F`, valida ID 1168 e então envia exatamente um `0x85`. Em qualquer erro antes da validação do ID, `0x85` não é enviado. Não há retry ou outros comandos. A saída JSONL inclui os pacotes TX/RX, resultado e índice ativo; não contém nenhuma operação de escrita.

Com acesso ao índice de pacotes, no host Fedora com o teclado conectado por USB e o usuário já autorizado a abrir a coleção HID, os comandos preparados são:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
.venv/bin/python tools/read_active_profile.py --timeout 2 --log docs/06-profile-hardware.jsonl
```

A instalação no ambiente virtual é necessária apenas se esse host não tiver hidapi disponível no ambiente Python ativo. Não usar `sudo` nem alterar permissões do sistema. A execução é uma única tentativa; diante de erro, não repetir sem investigar e decidir separadamente.

## Resultado, riscos e próximo passo

Não há resposta física para decodificar nem conclusão local sobre correspondência com o protocolo. O protocolo está comprovado no código e em testes simulados; a semântica `reply[1]` vem da fonte pública sharkfin, não da unidade observada. O risco de bloqueio do hidapi permanece: a deadline não cancela uma chamada nativa bloqueada.

Próxima etapa: executar manualmente o comando acima em Fedora com hidapi disponível e então anexar o JSONL produzido. Não recomendar qualquer outro teste físico neste ciclo. Não foram implementadas escritas nem alterações de firmware.

## Retificação do ciclo 6.5 — integração do registro

A tentativa posterior descrita em `docs/06.5-profile-integration.md` chegou ao roundtrip `0x8F`, mas a leitura de `client.last_exchange` interrompeu o script antes da validação do ID e da consulta `0x85`. Como a troca está registrada na conexão, o script agora coleta TX/RX e outcome de `connection.last_exchange`, sem declarar sucesso antes de validar a resposta do perfil. O JSONL físico existente foi preservado.

Regressões simuladas cobrem `0x8F` seguido por `0x85`, timeout de identificação sem RX/perfil fictícios e ID interno inesperado que bloqueia `0x85`. A suíte completa passou: **42 testes** com `.venv/bin/python -m unittest discover -s tests -v`. Nenhuma consulta física foi executada durante a correção 6.5. O próximo comando físico permanece manual e único, conforme o plano da seção acima.
