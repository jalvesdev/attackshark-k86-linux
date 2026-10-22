# Relatório do ciclo 5

## Resultado

Auditoria preservou as implementações dos ciclos anteriores e os 17 testes originais passaram antes das alterações. Foram corrigidas lacunas comprovadas: consultas agora são marcadas como yc500, família diferente falha fechada, seletores customizados são recusados pelo cliente, e o caminho de consulta física exige `allow_hardware=True` e confirma o ID interno 1168 na mesma conexão antes do GET. A descoberta continua exigindo VID/PID, interface, coleção e descritor esperados. Report ID 0 é enviado como byte externo seguido do relatório de 64 bytes e solicitado como relatório de 65 bytes; a API pode devolver com ou sem o prefixo, ambos são tratados. Roundtrips e fechamento do mesmo handle são serializados.

Todos os GETs yc500 documentados solicitados (incluindo extensões relevantes `0x88`, `0x8B`, `0x8C`, `0x97`) têm codificação/decodificação, limites de páginas/slots e fixtures sintéticas. Checksum de envio é validado nos testes. Não há regra documental de checksum de resposta, então não foi inventada. Consultas de configuração não são disparadas automaticamente. Nenhum comando SET ou inicializador de configuração foi acrescentado.

## Evidência

`sharkfin/docs/PROTOCOL.md` confirma os layouts usados e que `0x85` sem payload retorna o perfil ativo em `reply[1]`, zero baseado. A fonte classifica esses resultados como evidência do projeto comunitário [HW]/[FW]/[JS]; não substituem validação do firmware desta unidade. O ID local 1168 está confirmado pela resposta real preexistente a `0x8F`; família yc500 é a associação do catálogo sharkfin.

## Timeout

Hidapi não cancela portavelmente `get_feature_report` bloqueado. O timeout atual é observado após retorno ou mapeado de erro nativo. Não foi criada thread abandonável nem subprocesso sem necessidade de GUI. O documento de estratégia recomenda processo worker/watchdog no pai para eventual GUI e explica que isso não garante interrupção imediata do ioctl. Não há retry.

## Testes

Executado `python -m unittest discover -v`: **25 testes aprovados**. Inclui os 17 anteriores, codecs sintéticos, família, limites, checksum, valores inesperados, resposta inválida, recusa de dispositivos/consultas sem autorização, guarda de ID, serialização concorrente, timeout, falha/desconexão e abertura de sessão nova. Não houve consulta HID neste ciclo. As fixtures novas são sintéticas; a única fixture física existente é a identificação anterior `0x8F`.

## Próxima consulta proposta

Solicitar autorização para uma única consulta `0x85` de perfil ativo. Payload vazio; bytes do protocolo `85 00 00 00 00 00 00 7A` seguidos de 56 zeros; transporte acrescenta `00` como Report ID. A resposta valida tamanho/opcode e interpreta byte 1 como índice ativo. Plano, critérios, riscos e falha sem repetição estão em `05-hardware-validation-plan.md`. O teste não foi executado.

## Riscos restantes

- A semântica foi obtida da documentação pública sharkfin, não de execução local dos GETs.
- Parte dos índices/flags não tem domínio universal publicado; os decoders preservam valores em vez de fabricar limites ou significados.
- Hidapi pode bloquear além da deadline, e a biblioteca atual não pode interromper a chamada nativa.
- Firmware defeituoso/divergente pode reagir de modo inesperado mesmo a GET documentado.
