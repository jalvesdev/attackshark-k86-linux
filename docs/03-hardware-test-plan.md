# Ciclo 3 — plano de teste no hardware

> Atualização ciclo 4: a resposta física de identificação foi fornecida e registrada em `docs/03-identification-hardware.jsonl`; ID 1168 confirma a correspondência K86-1168. A anotação de bloqueio mais abaixo descreve somente a sessão do ciclo 3. Nenhuma consulta física adicional foi executada no ciclo 4; comandos de configuração continuam não testados.

## Situação

O teste físico está preparado, mas não autorizado nem executado. A variante interna permanece **não confirmada**. O VID:PID físico e a revisão USB `01.14` foram observados em sysfs; o ID sharkfin 1168 é apenas a expectativa do catálogo.

## Transação que requer aprovação

Na interface 2 do dispositivo USB `3151:4015`, enviar um único Feature Report de 64 bytes, report ID 0:

```text
8F 00 00 00 00 00 00 70 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

O transporte Linux envia os 65 bytes `00` + relatório acima em `HIDIOCSFEATURE(65)`, aguarda 10 ms e chama `HIDIOCGFEATURE(65)` com report ID 0. A ferramenta exige que o device node corresponda a VID:PID `3151:4015` e interface 2, e que a autorização explícita esteja presente.

Motivo para considerar a consulta segura: sharkfin define `0x8F` como identify/GET, declara o ID como resposta little-endian e usa o mesmo comando em todas as famílias. A fonte chama a operação de handshake e não documenta escrita de estado para ela. Riscos residuais: envio de um Feature Report ao teclado, resposta incompatível, timeout/stall do endpoint, necessidade de reconectar e possibilidade teórica de comportamento não documentado no firmware desta unidade.

## Execução após autorização

Primeiro, fora do sandbox do Codex, verifique dispositivo e permissões existentes sem alterá-las:

```sh
ls -l /dev/hidraw9 /dev/hidraw10 /dev/hidraw11
getfacl /dev/hidraw11
udevadm info --query=all --name=/dev/hidraw11
```

Em terminal host, no diretório do projeto, a simulação já executada pode ser repetida com:

```sh
python3 tools/identify_k86.py --simulate
```

Após autorização do proprietário, a invocação real será:

```sh
python3 tools/identify_k86.py --device /dev/hidraw11 --timeout 3 --log docs/03-identification-hardware.jsonl --authorize-send IDENTIFY-3151:4015
```

O caminho `hidraw11` corresponde à interface 2 na evidência desta sessão; confirmar novamente no host antes de usar. Se o usuário host não tiver acesso, usar apenas um método pontual e aprovado que não deixe alterações persistentes. A CLI não executa descoberta de outros dispositivos nem tenta fallback em interfaces.

## Critério de interpretação e pendências

- Resposta válida `8F 90 04 00 00 …` confirma a leitura do ID interno 1168 e a correspondência com a linha K86/yc500 no catálogo sharkfin.
- Qualquer outro ID deve ser registrado sem tentativa de comandos de família/configuração e tratado como dispositivo desconhecido até revisão documental.
- Timeout, resposta curta, opcode inesperado ou erro de ioctl encerram o teste; não repetir automaticamente nem fazer varredura.
- Nenhum comando de perfil, iluminação, keymap, macro, firmware, reset ou configuração faz parte deste plano.
- Pendente: acesso preexistente a `/dev/hidraw11` no host Fedora e registro do log real após executar a única tentativa autorizada.

## Registro da autorização e bloqueio de acesso (2026-10-22)

O usuário autorizou explicitamente uma única consulta `0x8F`, incluindo envio e leitura, sem repetição. Antes do envio, foram repetidas duas simulações na revisão final da ferramenta; ambas interpretaram a resposta simulada `8F 90 04 00 00 …` como ID decimal 1168. Sysfs/udev revalidaram `/sys/class/hidraw/hidraw11` como interface 2 do teclado USB `3151:4015` no caminho físico `1-1.2:1.2`. O receptor `3151:4011` está em `1-1.4` e é rejeitado pelo filtro da ferramenta.

**Resultado físico:** a tentativa foi interrompida antes do envio porque `/dev/hidraw11` não está exposto no sandbox. Bytes transmitidos: nenhum. Resposta recebida: nenhuma. Erro de transporte: não houve ioctl; o caminho de dispositivo está ausente. Estado do teclado: nenhuma operação foi feita nesta tentativa, portanto não há mudança causada por ela; estado funcional atual não foi consultado. Não se tentou contornar o sandbox, elevar privilégios, alterar permissões ou criar regra udev.

Para consumir a autorização já dada, execute diretamente no host Fedora, uma única vez, em um terminal com acesso preexistente ao nó:

```sh
python3 tools/identify_k86.py --device /dev/hidraw11 --timeout 3 --log docs/03-identification-hardware.jsonl --authorize-send IDENTIFY-3151:4015
```

O código executa exatamente um HIDIOCSFEATURE e um HIDIOCGFEATURE. Não repete em timeout, erro ou resposta inesperada. Se o comando falhar por `PermissionError`, pare; não altere permissões e não repita com `sudo` sem nova decisão. Depois que o usuário executar o comando no host, o log poderá ser anexado e interpretado sem outra consulta ao teclado.

Até existir resposta física, `yc3121` e `yc500` continuam **prováveis por catálogo**, não confirmados para esta unidade.
