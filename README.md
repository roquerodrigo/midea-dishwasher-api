# midea-dishwasher-api

Cliente Python para lava-louças Midea (`device_type 0xE1`, plugin v5).

Implementa o protocolo de aplicação `AA … E1` e a camada de transporte LAN V3
(handshake 8370 + AES-128-CBC + SHA-256, com framing V2 5A5A interno).

## Instalação

```bash
pip install midea-dishwasher-api[lan]
```

O extra `lan` instala `cryptography`, necessário para falar diretamente com a
máquina via LAN. Sem o extra, o pacote ainda expõe o codec do frame e o
parser de status para uso com transporte próprio (cloud, mock, etc.).

## Uso rápido

```python
from midea_dishwasher_api import BrightLevel, Client, Mode, V3Transport

with V3Transport(
    host="192.168.5.100",
    device_id=151732606394621,
    token=bytes.fromhex("..."),  # 64 bytes
    key=bytes.fromhex("..."),    # 32 bytes
) as transport:
    client = Client(send=transport)

    status = client.query_status()
    print(status.machine_state)   # MachineState.POWER_ON / POWER_OFF
    print(status.cycle_state)     # CycleState.IDLE / WORK / ORDER / ...
    print(status.left_time)       # minutos restantes (apenas em WORK)
    print(status.door_closed)
    print(status.bright_lack)     # secante acabou?

    client.power_on()
    client.start_to_work(mode=Mode.ECO, extra_drying=True)
    client.set_bright(BrightLevel.L3)
    client.cancel_work()
    client.power_off()
```

Os métodos de controle não retornam estado (a máquina demora alguns segundos
para refletir a mudança). Chame `query_status()` quando quiser estado fresco.

## API

### Client

| Método | Efeito |
|---|---|
| `query_status() -> DishwasherStatus` | Lê o estado atual |
| `power_on()` | Liga a máquina |
| `power_off()` | Desliga |
| `cancel_work()` | Cancela ciclo / volta ao idle |
| `start_to_work(mode, extra_drying=False)` | Inicia ciclo |
| `set_bright(level: BrightLevel)` | Ajusta o nível do abrilhantador (1–5) |

### DishwasherStatus

Campos decodificados da resposta:

- `machine_state: MachineState | None` — `POWER_ON` / `POWER_OFF`
- `cycle_state: CycleState | None` — `idle`, `order`, `work`, `error`, ...
- `wash_stage: WashStage | int | None` — `IDLE`, `PRE_WASH`, `MAIN_WASH`, `RINSE`, `DRY`, `FINISH`
- `error_code: ErrorCode | int` — `NONE`, `WATER_SUPPLY`, `HEATING`, `OVERFLOW`, `WATER_VALVE`
- `left_time: int | None` — minutos restantes (preenchido apenas quando `cycle_state == WORK`)
- `door_closed: bool`
- `bright_lack: bool` — secante (rinse aid) acabou

### Modos disponíveis (`Mode`)

`AUTO`, `INTENSIVE`, `NORMAL`, `ECO`, `GLASS`, `NINETY_MIN`, `ONE_HOUR`,
`RAPID`, `SOAK`, `THREE_IN_ONE`, `HYGIENE`, `QUIET`, `PARTY`, `FRUIT`.

## Transporte customizado

`Client` aceita qualquer `Callable[[bytes], bytes]` como `send`. Útil para
testes com transporte mock, integração com cloud, ou pipeline próprio:

```python
def fake_send(frame: bytes) -> bytes:
    return assemble_frame(b"...", 0x02)

client = Client(send=fake_send)
```

## Como obter `token` e `key`

São credenciais por dispositivo emitidas pela cloud da Midea. Use ferramentas
existentes (`midea-msmart`, `midea-beautiful-air`, `midea-discover`) para
extrair a partir da sua conta no app.

## Licença

MIT — ver `LICENSE`.
