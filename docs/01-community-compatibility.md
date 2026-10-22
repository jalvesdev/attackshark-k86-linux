# Compatibilidade comunitária — ATTACK SHARK K86

Pesquisa realizada em 2026-10-21. O conteúdo de repositórios comunitários é evidência de implementação/relato de terceiros, não um teste neste teclado.

## Identidade física e revisões

O registro de placas do projeto `sharkfin` lista três revisões K86, cada uma com controladora e família de protocolo distintas:

| Device ID reportado pelo projeto | VID:PID USB com fio | Controladora/família | Layout |
|---:|---|---|---|
| 1168 | `3151:4015` | `yc3121_sg8967_3m_soc`, `yc500` | Desenhado |
| 2730 | `3151:5002` | `yc3123_sg_sg8967_3m_1k`, `gen2` | Desenhado |
| 4094 | `3151:5056` | `ry6602_sg_sg8967_3m_1k_1k`, `gen2` | Conferência inicial do mapa necessária |

Tabela revisada pela ficha atual do K86 em 2026-10-21. A enumeração local `3151:4015` corresponde à linha 1168/yc500 por catálogo, mas o device ID interno da unidade ainda não foi consultado; classificação física final permanece provável, não confirmada. A ficha atual descreve para 4094 uma conferência inicial do mapa antes de edição por desenho.

O helper proprietário contém `3151:4011` na interface 2 como coleção HID de vendor com usage page `0xFFFF` e usage `0x02`, marcada `dongle_common`; contém também os PIDs com fio e uma entrada BLE `3151:4012`. A descrição USB local de `3151:4011` é `ROYUAN 2.4G Wireless Keyboard`. Essa convergência torna provável que o receptor conectado pertença à família K86, mas a identificação exata da unidade/revisão ainda depende de conectar o teclado por cabo e ler os dados de identificação.

## Modos de conexão

- **USB com fio:** rota preferida para investigação e futura configuração. As fontes comunitárias indicam mais de um PID/família, então não se deve escolher o protocolo somente pelo nome K86.
- **Receptor 2,4 GHz (`3151:4011` observado):** há evidência comunitária de um canal HID e relay em alguns receptores. O próprio projeto descreve suporte variável entre receptores; a unidade deve ser identificada em consulta não destrutiva.
- **Bluetooth:** o projeto `sharkfin` informa que o K86 não expõe canal de configurações nesse modo. Um fork antigo do OpenRGB também deixa o detector Bluetooth K86 comentado/não implementado. Não contar com controle de configuração por Bluetooth.

O documento de protocolo público descreve 64-byte Feature Reports para a família de teclados ROYUAN e separa famílias `yc500` e `gen2`; a semântica de alguns opcodes muda entre famílias. O K86 aparece na evidência de firmware `2730`/`yc3123`. Esses dados são úteis para orientar a investigação, mas não foram enviados ao teclado local nem reproduzidos de forma independente aqui. Não há implementação ou pacote de escrita nesta fase.

## Funcionalidades citadas para o K86

O catálogo K86 do `sharkfin` afirma suporte a remapeamento da camada base/Fn, três perfis embarcados, 18 efeitos de iluminação, RGB, cores por tecla, macros em 50 slots, debounce, temporizadores de suspensão, opções de dispositivo, backup/restauração e tela em revisões identificadas. Controles de knob e iluminação lateral dependem da revisão. Isso constitui evidência de capacidade alegada pelo projeto; não prova que o software Windows fornecido exponha cada item nem que a unidade conectada tenha todas as funções.

## Projetos encontrados

| Projeto | Resultado para o K86 | Avaliação para este trabalho |
|---|---|---|
| [sharkfin](https://github.com/dniminenn/sharkfin) | Configurador multiplataforma que lista explicitamente as três revisões K86 como graváveis; mantém catálogo e documento detalhado de protocolo. GPL-3.0-or-later; marcado como beta. | Referência comunitária mais completa. Revisar evidências e licenças; não copiar código nem adotar como dependência antes de decisão explícita. Suas notas alertam que transporte sem fio e famílias variam. |
| [Catálogo e revisão K86 do sharkfin](https://getsharkfin.com/boards/attack-shark-k86) | Lista os PIDs, controladoras, diferenças entre revisões e funções do K86. Informa USB como rota de escrita e Bluetooth sem canal de configuração. | Referência para identificar variante e montar matriz de capacidades. Não equivale a teste local. |
| [Protocolo ROYUAN do sharkfin](https://github.com/dniminenn/sharkfin/blob/master/docs/PROTOCOL.md) | Evidência declarada como hardware/firmware/código do fornecedor; descreve famílias distintas e transporte Feature Report. | Fonte para orientar análise independente. Há seções de firmware/bootloader que não fazem parte desta fase e não foram executadas ou reproduzidas. |
| [OpenRGB upstream](https://gitlab.com/CalcProgrammer1/OpenRGB) | Não foi encontrada comprovação de suporte K86 no upstream durante a busca. | Não presumir suporte por modelos ROYUAN/Epomaker próximos. |
| [Fork comunitário de OpenRGB](https://github.com/Rheyan-Shah/OpenRGB-kreo-swarm-intigration-/blob/master/Controllers/EpomakerController/EpomakerControllerDetect.cpp) | O detector do fork lista `3151:4015` como K86 USB, `3151:4011` como dongle partilhado com TH80 Pro e tem detector Bluetooth K86 comentado. | Código derivado, não prova que o upstream atual incorpore isso nem que o Bluetooth funcione. |
| [libratbag](https://github.com/libratbag/libratbag) | A busca encontrou proposta/issue para mouse Attack Shark X11, não suporte ao teclado K86. | Projeto orientado a periféricos de apontamento; não atende o objetivo de configurar o K86. |
| [OpenRazer](https://github.com/openrazer/openrazer) | O catálogo oficial lista dispositivos Razer, VID `1532`; o K86 usa VID `3151`. | Não aplicável ao K86. |
| [attackshark-k86-controller](https://github.com/navidicted/attackshark-k86-controller) | Projeto específico de tela/imagens, derivado de `epomaker-controller`; não é configurador completo. | Fonte adicional para a tela, se ela existir nesta revisão; não adotar antes de confirmar a variante. |

## Estratégia recomendada após este checkpoint

1. Enumerar por cabo USB e registrar VID:PID, interfaces e report descriptors via sysfs/kernel; ler o device ID interno apenas quando a interface de leitura puder ser acessada com segurança. A leitura ainda não ocorreu.
2. Confirmar qual família de protocolo corresponde à revisão presente e reconciliar isso com a tabela interna do helper e com evidência do REA.
3. Mapear funcionalidades do software Windows separando UI, frontend e helper nativo.
4. Só então selecionar uma consulta de leitura cujo comportamento e formato estejam documentados para aquela família. Continuar bloqueando escrita até validação independente e autorização do usuário.

## Fontes consultadas

- README de [Attack-Shark-K86](https://github.com/tsensei/Attack-Shark-K86), orienta alternar a chave física para `Win` e `USB` para usar o cabo.
- Repositório e docs do `sharkfin`, URLs acima.
- Detector de Epomaker/K86 no fork OpenRGB acima.
- [Pull requests do libratbag](https://github.com/libratbag/libratbag/pulls), para distinguir a proposta de mouse Attack Shark de suporte ao teclado.
- [Catálogo de dispositivos do OpenRazer](https://github.com/openrazer/openrazer/blob/master/README.md), para confirmar que esse projeto é voltado a dispositivos Razer.
