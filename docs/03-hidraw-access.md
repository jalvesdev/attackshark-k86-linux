# Ciclo 3 — acesso hidraw

Data da inspeção: 2026-10-22. Nenhum relatório foi enviado ao teclado físico.

## Evidências observadas

- Sysfs expõe `/sys/class/hidraw/hidraw0` a `hidraw11`. Os nós hidraw do teclado `3151:4015` são `hidraw9` (interface 0), `hidraw10` (interface 1) e `hidraw11` (interface 2). Os links apontam para as respectivas interfaces sob `/sys/bus/usb/devices/1-1.2`.
- `udevadm info` para `/sys/class/hidraw/hidraw9` informa `DEVNAME=/dev/hidraw9`, major/minor `241:9`, `ID_USB_INTERFACE_NUM=00`, `ID_USB_DRIVER=usbhid`, e links `by-id`/`by-path`. A enumeração do dispositivo USB retorna `3151:4015`, produto `Gaming_Keyboard`, revisão USB `0114`.
- As interfaces `1-1.2:1.0`, `:1.1` e `:1.2` informam `bInterfaceNumber` 00/01/02 e driver `usbhid`. Assim, o kernel associou as três interfaces HID esperadas.
- A coleção de classe hidraw no sysfs contém links para `hidraw9`–`hidraw11`, mas `/dev/hidraw*` não aparece na visão de `/dev` deste processo. Não há como obter `stat`, ACL, modo ou grupo dos device nodes a partir deste namespace.
- Processo atual: UID 1000, grupo principal 1000, grupo adicional 65534 (`nobody`), `NoNewPrivs: 1`, `Seccomp: 2`. Isso é compatível com isolamento de sandbox e visibilidade de `/dev` limitada. Não prova, isoladamente, a configuração de sandbox do host.
- `udevadm` consegue consultar sysfs e metadados do evento, mas a ausência do nó em `/dev` impede testar `open(2)` ou confirmar permissões host. A ferramenta `lsusb` está instalada, mas relatórios anteriores registram falha libusb `-99`.

## Diagnóstico delimitado

O kernel e udev enumeraram o dispositivo e criaram os objetos hidraw. A causa imediata da indisponibilidade para este processo é a ausência dos nós em seu `/dev`, não a falta de driver HID ou de interfaces. Como os nodes não estão montados/expostos no namespace, não é possível concluir se o usuário `zexman` no host teria acesso pelos modos/ACL/grupos. Não foi feito `chmod`, alteração de regra udev, nem mudança persistente.

### Revalidação para a tentativa autorizada (2026-10-22)

`udevadm info --query=all --path=/sys/class/hidraw/hidraw11` voltou a identificar `DEVNAME=/dev/hidraw11`, `ID_VENDOR_ID=3151`, `ID_MODEL_ID=4015`, `ID_USB_INTERFACE_NUM=02`, `ID_USB_DRIVER=usbhid`, caminho USB `1-1.2:1.2` e symlink `usb-ROYUAN_Gaming_Keyboard-if02-hidraw`. Sysfs confirma `bInterfaceNumber=02` e driver `usbhid`. A consulta `ls -l /dev/hidraw11` falhou porque esse caminho não existe na visão `/dev` do processo. O receptor continua sendo outro USB device, `1-1.4`, VID:PID `3151:4011`; a CLI filtra estritamente `3151:4015` e interface `02`.

Após autorização explícita, a tentativa física não foi iniciada porque o nó continua inacessível neste sandbox. Nenhum relatório foi transmitido. Não tentamos elevar privilégios nem acessar um namespace externo.

Para verificar no Fedora host, em um terminal normal fora do Codex:

```sh
ls -l /dev/hidraw9 /dev/hidraw10 /dev/hidraw11
getfacl /dev/hidraw9 /dev/hidraw10 /dev/hidraw11
udevadm info --query=all --name=/dev/hidraw11
udevadm test "$(udevadm info --query=path --name=/dev/hidraw11)"
```

O processo host deve confirmar que `/dev/hidraw11` é interface 2 e que seu usuário já tem acesso. Caso a leitura seja necessária, execute a CLI fornecida diretamente em um terminal host com os privilégios já existentes. Se o host negar acesso, a alternativa controlada é uma invocação pontual autorizada (por exemplo, `sudo` apenas para essa execução), sem alterar modo, grupo, ACL ou regra permanente. A CLI recusa qualquer outro VID:PID/interface antes de enviar.

## Referências do projeto

Os relatórios anteriores `docs/00-environment-report.md` e `docs/02-device-identification.md` documentam a primeira observação do sysfs e descritores. Esta sessão confirma a existência atual dos objetos `hidraw` em sysfs e a ausência dos nós em `/dev` do processo isolado.
