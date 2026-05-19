# AI report
## Které technologie byly použity?
AI chatboty použity při tvoření aplikace:
- Gemini 3.1 PRO

## Příklady použitých promptů:
```
#Example error message
Why did this happen?
```

```
in python how can I generate a UUID?
```


## Co AI vygenerovala správně?
Pro první příklad našel v kódu chybu, omylem jsme napsali "" do [] při prohledávání prvků v metadata
```Chyba je v tom, že metadata (načtená z JSONu) je dictionary (slovník). Když napíšeš for file in metadata:, Python prochází jen klíče (což jsou textové řetězce, tedy tvoje ID souborů), nikoliv samotné objekty. Proto se snažíš z textu číst pomocí ["id"], což vyhodí chybu.```


A pro druhý příklad vygeneroval rozumnou funkci pro generování UUID:
```
import uuid
```

# Generate a random UUID
```
my_uuid = uuid.uuid4()
```


## Jaké chyby AI udělalo?

Zatím nic.



# Evoluce databáze: Alembic, Buckety a Účtování

## Které technologie byly použity?
AI chatboty použity při tvoření aplikace:
 - Gemini 3.1 PRO

## Příklady použitých promptů:
``How to use Alembic with SQLAlchemy models in FastAPI?``

``Why does SQLite fail when adding NOT NULL column with Alembic?``


## Co AI vygenerovala správně?
- AI pomohla s pochopením práce s Alembicem, konkrétně jak propojit existující SQLAlchemy modely s migračním systémem (nastavení `target_metadata` v `env.py`). 

 - Dále správně vysvětlila problém při migraci v SQLite, kdy nelze přidat sloupec s `NOT NULL` bez výchozí hodnoty, což pomohlo opravit migraci nastavením `nullable=True`.

## Jaké chyby AI udělalo?
AI občas navrhovala řešení bez ohledu na omezení SQLite (např. přidání `NOT NULL` sloupce bez defaultní hodnoty), což vedlo k chybě při migraci. Bylo nutné úpravy provést ručně.


# Propojení FastAPI, Message Brokeru a Workeru

## Které technologie byly použity?
AI chatboty použity při tvoření aplikace:

ChatGPT

## Příklady použitých promptů:
```text
Jak mám propojit FastAPI API s WebSocket message brokerem?
```

```text
Proč mi worker padá, když dostane zprávu z brokeru?
```

```text
Kam mám vložit await ws.send(...) ve workeru?
```

## Co AI vygenerovala správně?
AI pomohla pochopit, že message broker neběží jako klasická Python knihovna s funkcí publish(), ale jako samostatná WebSocket služba. Díky tomu bylo nutné z FastAPI endpointu vytvořit WebSocket klienta, který pošle zprávu brokeru ve formátu:

```python
message = {
"action": "publish",
"topic": "image.jobs",
"payload": {
"operation": data.operation,
"image_path": data.image_path
}
}
```

AI také správně navrhla worker, který se přihlásí k topicu image.jobs, čeká na zprávy z brokeru a po zpracování obrázku odešle zprávu na topic image.done:

```python
await ws.send(json.dumps({
"action": "publish",
"topic": "image.done",
"payload": {
"status": "done",
"file": "output_" + path
}
}))
```

Dále AI pomohla vyřešit problém, kdy worker padal při prázdné nebo nevalidní zprávě z brokeru. Řešením bylo přidat kontrolu, zda zpráva obsahuje operation a image_path. Pokud ne, worker zprávu ignoruje a pokračuje dál:

```python
if not operation or not path:
print("Ignoruju špatnou zprávu:", payload)
continue
```

To zabránilo pádu workeru například ve chvíli, kdy broker poslal zprávu bez potřebného payloadu.

AI také pomohla vyřešit problém s await ws.send(), protože odeslání zprávy zpět do brokeru musí probíhat uvnitř asynchronní funkce async def worker() a uvnitř aktivního WebSocket spojení. Díky tomu worker po dokončení úlohy může publikovat informaci o hotovém zpracování.

## Jaké chyby AI udělalo?
AI nejdříve předpokládala, že message broker bude možné používat přímo jako Python objekt pomocí metody typu broker.publish(). Ve skutečnosti ale broker fungoval jako samostatná WebSocket aplikace, takže bylo nutné řešení upravit a komunikovat s ním přes websockets.connect().