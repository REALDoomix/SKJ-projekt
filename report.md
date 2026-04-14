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