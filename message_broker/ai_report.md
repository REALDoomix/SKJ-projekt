# AI Report

## 1. Vysvětlení zadání

Pomocí AI jsem si nechal vysvětlit zadání projektu, konkrétně princip Message Brokeru a návrhového vzoru Publish/Subscribe.

AI mi pomohla pochopit:

* rozdíl mezi synchronní a asynchronní komunikací
* jak funguje Pub/Sub model (publisher, subscriber, broker)
* proč se používají topics a jak probíhá routing zpráv

Díky tomu jsem lépe porozuměl architektuře aplikace a mohl správně implementovat základní broker.

---

## 2. Práce s MessagePack (encode/decode)

AI jsem využil také při implementaci podpory MessagePack.

Konkrétně mi pomohla:

* pochopit rozdíl mezi JSON (textový formát) a MessagePack (binární formát)
* implementovat funkce pro serializaci a deserializaci (`encode` / `decode`)
* upravit komunikaci mezi klientem a serverem tak, aby podporovala oba formáty

Díky tomu aplikace splňuje požadavek zadání na podporu více formátů zpráv.
