# Identificação USB do K86 — ciclo 2

> Atualização ciclo 4: uma resposta física ao `0x8F` está preservada em `docs/03-identification-hardware.jsonl`, confirmando o ID interno 1168 e a correspondência K86-1168. As notas abaixo refletem o estado no fechamento do ciclo 2. `yc3121` e `yc500` permanecem associações do catálogo.

Data: 2026-10-21. Nenhum relatório HID foi enviado/lido neste ciclo e nenhum comando de escrita foi enviado.

## Dispositivos observados

A enumeração já registrada em `docs/00-environment-report.md` e repetida em sysfs nesta sessão mostra o teclado em `/sys/bus/usb/devices/1-1.2` como `3151:4015` (`ROYUAN`, `Gaming Keyboard`, bcdDevice `01.14`) e o receptor em `/sys/bus/usb/devices/1-1.4` como `3151:4011` (`ROYUAN`, `2.4G Wireless Keyboard`, bcdDevice `05.02`). A unidade com fio e o receptor estão conectados simultaneamente; portanto, o receptor não foi usado como substituto da identificação do teclado. O headset Logitech e seu receptor também aparecem na enumeração.

O teclado expõe três interfaces HID, todas associadas a `usbhid`: interface 0 boot keyboard (interrupt IN `0x81`, 8 bytes); interface 1 HID não boot, com teclado/multimídia e coleção vendor-defined (Report ID 5, entrada de 3 bytes; interrupt IN `0x82`, 16 bytes); interface 2 coleção vendor-defined (Feature Report ID implícito 0, 64 bytes; interrupt IN `0x83`, 8 bytes). Os descritores foram obtidos do sysfs/kernel e registrados na investigação anterior. `lsusb` continua falhando com erro libusb `-99`; isso não impediu a enumeração por sysfs. Não há `/dev/hidraw*` visível neste ambiente, embora udev tenha anteriormente anunciado `hidraw9` para o dispositivo. Não alterei permissões nem regras udev.

## Revisão provável e limite da identificação

O catálogo atual do sharkfin relaciona `3151:4015` ao device ID 1168, controlador `yc3121_sg8967_3m_soc`, protocolo `yc500` e layout desenhado. Logo, a revisão física é **provavelmente a variante K86 1168/yc500**. Não foi lido o identificador interno do teclado; a própria documentação sharkfin diz que ele deve ser obtido pela consulta `0x8F`. Como não havia hidraw acessível e o escopo não autorizou esse acesso no dispositivo, não classifico a revisão interna como confirmada. O PID, fabricante/produto e bcdDevice são observados diretamente; a associação K86/1168/yc500 vem do catálogo comunitário.

O relatório `docs/01-community-compatibility.md` tinha uma linha imprecisa que associava PID `3151:5002` ao nome de família `gen2` sem descrever explicitamente as evidências por revisão; a tabela definitiva do catálogo lida neste ciclo confirma: 1168=`3151:4015`/yc500, 2730=`3151:5002`/gen2 e 4094=`3151:5056`/gen2. O modelo inclui placas/controladores diferentes sob o mesmo nome K86. Não escolha opcodes apenas pelo nome do produto ou pelo PID.

## Reprodutibilidade e pendências

Fontes locais: `/sys/bus/usb/devices/1-1.2/{idVendor,idProduct,bcdDevice,manufacturer,product}` e `/sys/bus/usb/devices/1-1.2:1.{0,1,2}/`, conforme a captura anterior dos descritores. A leitura de `idVendor`, `idProduct` e `product` foi repetida; os nós hidraw continuam ausentes. O próximo passo para fechar a revisão é tornar o nó hidraw disponível ao processo por ação explícita do operador/ambiente (sem mudança automática de permissões) e obter somente o identificador de dispositivo por leitura documentada, após confirmar a interface e a semântica. Até lá, a versão final do hardware e a compatibilidade prática permanecem não comprovadas.
