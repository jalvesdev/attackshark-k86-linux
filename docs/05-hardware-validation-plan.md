# Plano para próxima validação física

## Estado no ciclo 6

O usuário autorizou a consulta única `0x85`, com identificação `0x8F` na mesma conexão. O pré-voo local não pôde enumerar/abrir HID porque o ambiente não possui o módulo Python `hid` e não expõe nós `/dev/hidraw*`. Nenhum comando foi enviado. O relatório do ciclo 6 e procedimento para Fedora estão em [`06-cycle-report.md`](06-cycle-report.md).

## Operação selecionada para aprovação

Uma consulta `0x85` de perfil ativo. A semântica no protocolo sharkfin é GET sem argumento: resposta `reply[1]` contém índice zero baseado do perfil atualmente ativo. Isso corresponde à intenção de identificar o perfil ativo no K86-1168; não lê um perfil indicado pelo host. Fonte: [sharkfin `docs/PROTOCOL.md`, Profiles](https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md#profiles), operação marcada [HW] pelo projeto comunitário. A unidade local já foi identificada como ID 1168 pela evidência anterior; nenhum `0x85` foi enviado aqui.

## Bytes e expectativa

O pacote de protocolo tem 64 bytes: byte 0 `85`, bytes 1..6 zero, byte 7 checksum Bit7 `7A`, bytes 8..63 zero. O transporte hidapi passa 65 bytes com Report ID zero inicial:

```text
00 85 00 00 00 00 00 00 7A 00 00 00 00 00 00 00 ... (65 bytes total)
```

Antes dele, a guarda de sessão transmite identify `0x8F` (já autorizado em ciclo anterior), valida `8F 90 04 00 00 ...` como ID 1168, tudo na mesma conexão. Espera-se resposta de 64 bytes com opcode `85` e byte 1 com o índice ativo. A documentação não garante quantidade máxima de perfis comum a todos os modelos; qualquer byte é preservado como índice, e a confirmação visual do índice deve vir da interface do fabricante, se disponível. Resposta curta, opcode divergente, timeout ou ID diferente interrompe o procedimento sem retry.

## Risco e procedimento

Risco baixo relativo a alterações: é um GET documentado, sem payload seletor e sem campo de escrita. Ainda transmite um Feature Report ao firmware local; resposta/stall inesperado, firmware diferente e bloqueio do endpoint continuam riscos residuais. Não afirmar ausência de efeitos colaterais não documentados.

Quando houver aprovação explícita para esse teste: conectar por USB com fio, encerrar software concorrente do teclado, identificar exatamente uma coleção USB `3151:4015`, interface 2, uso `FFFF:0002`, validar descritor de Feature Report ID 0 / 64 bytes e confirmar ID 1168. Transmitir uma vez o pacote acima e ler uma vez. Não repetir em falha. Anotar bytes TX/RX, horário, metadados HID e resultado. Se falhar, fechar a sessão; aguardar desconexão/reconexão do teclado se o endpoint parecer travado. Não usar `sudo` para contornar permissão sem decisão separada.

**Critérios de sucesso:** ID 1168 confirmado na sessão; transmissão única 65 bytes; resposta 64 bytes (com ou sem prefixo Report ID zero conforme backend), opcode `85`; byte 1 registrado sem interpretação inventada; sessão fechada. Falha em qualquer critério: interromper, preservar erro/bytes disponíveis, sem retry. Este plano não executa o teste nem concede autorização para ele.
