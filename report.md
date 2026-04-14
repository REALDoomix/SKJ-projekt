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

#Generate a random UUID
my_uuid = uuid.uuid4()
``````


## Jaké chyby AI udělalo?

Zatím nic.

# Úkol alembic, Buckety a Účtování

## Příklady použitých promptů:


```
>Měl bych použít Starlette pro middleware, nebo už to některá z importovaných knihoven zvládá?

>>Knihovna FastAPI má zabudovanou jednodušší metodu přes @app.middleware("http") decorator, nebo ještě simplističtější - použíjte Dependency injection
```

