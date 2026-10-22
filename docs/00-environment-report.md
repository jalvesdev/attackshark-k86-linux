# Relatório do ambiente — fase 0

Data da inspeção: 2026-10-21

## Ambiente

| Item | Resultado observado |
|---|---|
| Distribuição | Fedora Linux 44 |
| Kernel | `7.2.5-200.fc44.x86_64` |
| Arquitetura do host | x86_64 |
| Sessão gráfica | Wayland, Hyprland |
| Python | CPython 3.14.7 |
| `lsusb` / `usb-devices` / `udevadm` | Presentes |
| `file`, `sha256sum`, `strings`, `readelf`, `objdump` | Presentes |
| Ghidra, Hopper, IDA locais | Não encontrados no PATH |
| 7-Zip | 26.02 |
| Repositório Git | Não inicializado neste diretório |
| Módulos Python `pefile`, `lief`, `dnfile`, `PySide6`, `hid`, `usb` | Ausentes |

Os módulos Python não foram instalados. A inspeção das fases 0 e 1 não exige essas dependências.

## REA MCP

REA está conectado e respondeu a chamadas reais de análise. Os contratos consultados incluem `open_binary`, `binary_overview`, `inspect_artifact` e `list_documents`; a enumeração expôs também operações para strings, funções, pseudocódigo, referências e recursos PE. O provedor profundo observado foi Ghidra 12.1.4, integrado pelo REA, embora Ghidra não esteja disponível como comando local.

O arquivo fornecido (stub do instalador) foi aberto no REA como PE x86. O hash retornado pelo REA coincide com o cálculo local. A visão geral gerou evidência com 269 procedimentos, 237 strings e imagem base `0x400000`. Um segundo alvo, o helper nativo, também foi aberto no REA; a visão geral e uma busca de strings excederam o limite de 300 segundos e retornaram timeout. O parser PE de recursos do REA processou o helper sem disassembler e encontrou 11 entradas de recurso. Portanto, ainda não há pseudocódigo nem mapa de chamadas do helper no relatório.

O inventário genérico do REA considerou apenas o EXE externo e não reconheceu suas entradas NSIS internas. A limitação foi complementada pela listagem estática do 7-Zip. Nenhum executável foi iniciado.

## Teclado e USB

`lsusb` falhou com `unable to initialize libusb: -99`. `usb-devices`, sysfs e udev permitiram observar dispositivos USB conectados. Após conectar o K86 por cabo, a unidade com fio foi enumerada separadamente do receptor:

| VID:PID | Identificação reportada | Interfaces observadas |
|---|---|---|
| `3151:4011` | Fabricante `ROYUAN`, produto `2.4G Wireless Keyboard` | 3 interfaces HID; endpoints interrupt IN `0x81` (8 bytes), `0x82` (16 bytes), `0x83` (8 bytes) |
| `3151:4015` | Fabricante `ROYUAN`, produto `Gaming Keyboard` | 3 interfaces HID; endpoints interrupt IN `0x81` (8 bytes), `0x82` (16 bytes), `0x83` (8 bytes) |
| `046d:0a5b` | Logitech G933 Gaming Wireless Headset | 4 interfaces, incluindo HID |
| `046d:c53f` | Logitech USB Receiver | 3 interfaces HID |

O usuário confirmou que o modelo investigado é o Attack Shark K86. O `3151:4011` conectado é identificado pelo sistema como receptor `ROYUAN 2.4G Wireless Keyboard`; a pesquisa específica encontrou esse VID:PID associado ao dongle do K86 em fontes comunitárias, então é uma correspondência provável, mas o report descriptor e a resposta de identificação interna do teclado ainda não foram lidos.

O receptor `3151:4011` está em `/sys/bus/usb/devices/1-1.4`, revisão `05.02`. A unidade com fio `3151:4015` está em `/sys/bus/usb/devices/1-1.2`, revisão `01.14`, fabricante reportado `ROYUAN`, produto `Gaming Keyboard`, velocidade 12 Mbit/s. O VID:PID com fio coincide com o ID que a tabela comunitária do K86 associa a uma revisão yc500; essa correlação não prova por si só a revisão interna.

Na unidade com fio, interface 0 é HID boot keyboard (protocolo 1), interrupt IN `0x81` (8 bytes); interface 1 é HID sem subclass/protocolo boot, interrupt IN `0x82` (16 bytes); interface 2 é HID sem subclass/protocolo boot, interrupt IN `0x83` (8 bytes). O kernel associa `usbhid` às três. O sysfs expõe os três report descriptors: a interface 0 descreve teclado padrão; a interface 1 inclui controles multimídia, relatório de teclado estendido e uma coleção vendor-defined com Report ID 5 e 3 bytes de entrada; a interface 2 é vendor-defined e declara Feature Report ID implícito 0 com 64 bytes. Isso descreve o formato anunciado pelo dispositivo, sem ler nem enviar relatórios.

O udev anuncia `/dev/hidraw9` para a interface 0, com links em `/dev/input/by-id/usb-ROYUAN_Gaming_Keyboard-hidraw` e `by-path`. Porém, o nó `/dev/hidraw9` não está visível neste ambiente de execução. A existência do descritor em sysfs demonstra enumeração HID, mas ainda não permite abrir hidraw a partir deste processo. `lsusb` continua falhando com `unable to initialize libusb: -99`.

## Riscos e dados pendentes

- Confirmar no teclado/manual o modo físico utilizado; o sistema já enumera `3151:4015` por cabo, mas o modo seletor não foi observado.
- Tornar o nó hidraw visível para a aplicação de análise e verificar a enumeração hidraw das interfaces vendor-defined. Nenhum relatório foi lido/escrito.
- Verificar os projetos Linux existentes após confirmar VID/PID e a identidade exata do hardware.
- Os relatórios nesta fase não avaliam segurança de execução do instalador; somente análise estática foi feita.

## Estratégia recomendada

1. Identificar no helper nativo as APIs importadas e mapear, com o REA/Ghidra, os caminhos de descoberta e comunicação.
2. Inspecionar os recursos, metadados e arquivos do pacote sem executar os binários.
3. Correlacionar a identificação do helper com o dispositivo USB e, se necessário, obter captura USBPcap/Wireshark em Windows.
4. Não enviar relatórios de escrita nem alterar memória do teclado nesta etapa.

## Evidências desta fase

- `file`, SHA-256, `objdump`, `strings`, `7z l`, `usb-devices` e `udevadm` executados localmente.
- REA `open_binary` e `binary_overview` executados no PE principal.
- REA `open_binary` executado no helper; buscas de strings e visão geral nele expiraram após 300 s. `inspect_pe_resources` funcionou e enumerou 11 entradas.
- REA `inspect_artifact` executado; o resultado sinalizou que o formato específico do instalador exigia análise adicional.
- Nenhum pacote instalado e nenhuma configuração do sistema ou do teclado alterada.
