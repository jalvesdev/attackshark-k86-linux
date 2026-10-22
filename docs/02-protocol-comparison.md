# Comparação: software Windows, sharkfin e unidade física

> Atualização ciclo 4: o ID interno físico foi lido como 1168 em `docs/03-identification-hardware.jsonl`; portanto a identificação K86-1168 está confirmada. A tabela abaixo preserva o estado de validação no ciclo 2: nenhuma operação além de identificação foi testada no hardware. Controlador `yc3121` e família `yc500` continuam sendo dados de catálogo.

Escopo: comparação estática e documental. Não houve captura USB do software original nem teste de configuração no teclado físico. “Compatível” indica associação plausível por PID/catalogação; “validado no hardware” exige interação observada com a unidade e não está satisfeito por documentação de terceiros.

| Função / comando | Confirmado no software Windows | Implementado no sharkfin | Compatível com unidade local `3151:4015` | Validado no hardware local | Estado / evidência pendente |
|---|---|---|---|---|---|
| Enumerar dispositivo | Sim: RPC `watchDevList`; helper tem tabela `3151:4015` interface 2 | Sim: catálogo/seleção por device ID | Provável | Não | ID interno 1168 precisa leitura segura; hidraw não acessível |
| Identificar device ID (`0x8F`) | UI/helper genéricos expõem send/read; opcode não correlacionado ao driver Windows com certeza | Sim, documentado para ROYUAN; ID 1168 ligado ao K86 `4015` | Provável, família yc500 | Não | Não emitir até preparar etapa explicitamente autorizada |
| Keymap base e Fn | UI tem telas/ações; bytes exatos no bundle precisam mapeamento por fluxo completo | Sim, yc500 e gen2 com codecs diferentes | Provável para yc500 | Não | Primeiro confirmar ID interno; depois validar leitura de keymap e mapa físico |
| Perfis | UI tem gerenciamento de perfis | Sim; três declarados, opcodes variam por família | Provável | Não | Capacidade e quantidade não confirmadas localmente |
| RGB / efeitos | UI contém editores/tipos genéricos e chamada `sendMsg`/`setLightType` | Sim; catálogo anuncia 18 efeitos | Provável | Não | Atribuição exata de modelos UI ao K86 e pacotes yc500 ainda precisa fechar |
| Cor por tecla | Estados/funções genéricos presentes | Sim, padrão por tecla | Provável | Não | Presença no K86 local não validada |
| Macros | UI contém editor/armazenamento genéricos | Sim; 50 slots declarados | Provável | Não | Layout dos registros/limites do board local não testados |
| Debounce | Não associado por fluxo ao K86; UI genérica | Sim, yc500 1–10; opcode difere em gen2 | Provável | Não | Não escrever; verificar família antes de usar |
| Sleep timers / opções | UI possui configurações genéricas; RPC de baixo nível existente | Sim; yc500/gen2 usam offsets e opcodes distintos | Provável | Não | Precisa device ID e mapeamento do painel K86 |
| Knob / edge light / tela | Bundle contém componentes genéricos, mas associação à revisão não demonstrada | Knob e edge light listados para IDs 2730/4094; display com suporte descrito para 1168/2730 | Parcial e dependente da revisão | Não | Unidade física não inventariada em recursos visuais/botões; distinguir funções por ID |
| Receptor 2,4 GHz | Helper lista `4011` como dongle common; comportamento não analisado | Relays variam por receptor; cable recomendado | Incerto | Não | O receptor local pode ser K86, mas associação não prova relay; sem consultas ao dongle |
| Bluetooth | Helper tem ID BLE `4012` genérico | Sem canal de configuração alegado para K86 | Não estabelecido | Não | Não tratar ID BLE como suporte de configuração |
| Flash de firmware | Não confirmado como função UI executável para esta unidade | Sharkfin declara não fazer flash | Fora de escopo | Não | Não investigar/escrever nesta fase |

## Classificação resumida

- **Confirmado no software original:** transporte gRPC-Web e chamadas genéricas `sendMsg`, `readMsg`, `sendRawFeature`, `readRawFeature`; telas/ações genéricas de teclas, RGB, perfis e macros. Ainda não foram ligados a cada pacote físico do K86.
- **Implementado no projeto comunitário:** funções descritas na ficha K86 e protocolos yc500/gen2 documentados. A ficha e o protocolo são declarações do projeto comunitário, algumas evidências anotadas `[HW]`; não equivalem a teste da unidade deste projeto.
- **Compatível com revisão física:** provável K86 device ID 1168/yc500 por `3151:4015`; revisão interna ainda não lida. Não declarar funções “compatíveis” além da família provável.
- **Validado em hardware real local:** somente enumeração USB e report descriptors via sysfs. Nenhum comando do protocolo de configuração foi validado na unidade.
- **Desconhecido:** ID interno, resposta da unidade a consultas, semântica completa do helper, mapeamento das telas do software fornecedor para o K86, comportamento wireless e qualquer gravação persistente.

Recomendação: resolver o acesso à interface hidraw por procedimento explícito do operador; ler apenas o identificador documentado e confirmar `1168`; então, em etapa futura, desenhar testes de leitura com risco e recuperação revisados antes de iniciar qualquer escrita. Não implementar a interface Linux ainda.
