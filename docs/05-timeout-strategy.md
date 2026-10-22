# Ciclo 5 — timeout e bloqueio HID

## Limite observado

A chamada Python hidapi `get_feature_report(report_id, length)` usada pelo backend não oferece parâmetro portátil para cancelar uma chamada já bloqueada. A opção `timeout` da biblioteca mede o tempo da troca, mas não interrompe uma chamada nativa: a deadline só pode ser verificada depois que ela retorna. Um `TimeoutError` nativo é mapeado; chamada bloqueada não pode ser convertida com segurança em timeout por uma thread Python. O handle serializa roundtrips e o fechamento; portanto, chamar `close()` em outra thread também aguarda a chamada bloqueada, sem cancelá-la.

Não se deve abandonar uma thread bloqueada, iniciar segunda consulta, fechar o mesmo handle concorrentemente nem reutilizar um transporte potencialmente inconsistente. A implementação é síncrona, serializada pelo fluxo de chamada, sem retry ou watchdog fictício. O chamador deve manter operações curtas fora da thread da interface gráfica.

## Opções para futura GUI

- **Worker thread:** mantém a tela responsiva, mas não cancela o ioctl; uma thread bloqueada pode continuar viva. Não é mecanismo de timeout nem de recuperação.
- **Processo worker com watchdog no processo pai:** isola a interface e permite ao pai declarar falha e solicitar encerramento do worker. Encerrar o processo não garante que todo kernel/backend libere imediatamente o handle ou o dispositivo; o pai não deve reutilizar estado daquele worker e deve aguardar encerramento/reenumerar antes de criar uma nova sessão.
- **Recuperação:** em timeout comprovado, não repetir automaticamente. Marcar a sessão como indisponível; após o worker terminar, descartar conexão e handles, reenumerar e exigir nova ação explícita. Se o worker não terminar ou o endpoint permanecer travado, orientar desconexão/reconexão física antes de nova tentativa.

## Escolha neste ciclo

Não adicionar processo supervisor/watchdog ao pacote: não existe GUI ainda e não foi demonstrada necessidade para a CLI síncrona. Para uma GUI futura, a fronteira de processo é a opção mais segura para preservar responsividade, com a limitação acima; implementar apenas quando o fluxo da GUI e o comportamento real de encerramento forem validados. A biblioteca atual não promete um limite rígido de retorno para `get_feature_report`.
