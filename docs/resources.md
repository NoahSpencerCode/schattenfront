# ZERO HOUR: 1939 — The Resource Economy

How oil, steel and food are **made** and **spent**. Every figure here
is read from the code, not from memory: `config.py` holds the
constants, `game.py` the machinery, `units.py` the material costs.

---

## 0. The shape of it

Three resources, and each governs a **different half of the war**.
That separation is the whole design: no two of them are ever a tax
on the same decision.

| | governs | spent when | never spent on |
|---|---|---|---|
| **OIL** | operations | supply flows into a **machine**; an aircraft takes off | men, railways, production |
| **STEEL** | production | a factory builds a **piece of equipment** | movement, men |
| **FOOD** | manpower | a city **musters** men; every day, by **population** | machines, production |

National stockpiles, capped at **999** each (`RESOURCE_CAP`).
Only the five playable powers keep books — the NPC garrison nations
run no economy, so their deposits matter only when captured,
courted, or embargoed.

Opening stores: **400 oil, 800 steel, 260 food**
(`STARTING_RESOURCES`).

---

## 1. CREATION — where tons come from

### 1.1 Deposits (the map)

48 deposits stand beside their historical cities as real structures
(`config.DEPOSITS` → `structures.Deposit`). **Own the city, work the
deposit**; capture the city and the deposit changes flag with it,
with a fax naming the prize. Output is tons *per fortnight*.

| | sites | world output/ftn |
|---|---|---|
| oil | 9 | 640 |
| steel | 13 | 810 |
| food | 26 | 1,830 |

*Oil* — Ploiești 90, Baghdad 60, Tehran 60, Houston 120, Oklahoma
City 60, Palembang 80, Novorossiysk 100, Kuybyshev 40, Rangoon 30.

*Steel* — Essen 110, Pittsburgh 120, Birmingham 80, Chicago 60,
Stalingrad 60, Kharkov 60, Osaka 60, Mukden 60, Glasgow 40, Gorky
40, Liège 40, Prague 40, Milan 40.

*Food* — 26 granaries: the Ukraine (Kiev 110, Odessa 80, Rostov 70,
Voronezh 90), the American plains (St. Louis 110, Kansas City 100,
Omaha 90, Minneapolis 80), the paddies (Bangkok 90, Mandalay 80,
Saigon 80, Delhi 80, Calcutta 70, Nanking 70), the Danube (Budapest
60, Bucharest 60), France (Paris 60, Lyon 50, Bordeaux 50), and
scattered smaller fields (Sydney 70, Königsberg 50, Surabaya 50,
Munich 40, Nagoya 40, Bologna 40, Wuhan 60).

> A city works **one** deposit — `DEPOSITS` is keyed by city name, so
> a second entry for the same town silently replaces the first. The
> test suite asserts no site has been overwritten.

### 1.2 The civilian baseline

Every power draws a small neutral-market import regardless of what
it holds: **40 oil, 60 steel, 40 food** per fortnight
(`BASELINE_IMPORTS`). It is why a power stripped of every field
still trickles.

### 1.3 Daily accrual — the wells run every day

`_daily_income(country)` = (deposits + baseline) ÷ 14.
`_accrue_resources(days)` runs off the main loop whenever the day
counter turns, so tons arrive **daily, not in a fortnightly lump**.

This is deliberate: under the old lump model a power that ran dry on
the 3rd sat idle until the books closed. Now the granary that failed
this morning is paying again tomorrow.

The fortnight rollover (`_collect_resources`) no longer pays
anything — it only **closes the books**: it builds the itemised flow
report the top-bar tooltips and Quartermaster's Ledger read from,
then resets the spending meters.

### 1.4 Treaties

Cargo bought at the negotiating table arrives on **settlement day**
(the fortnight), not daily — `_settle_trade()` runs first at
rollover. Three shapes:

- **purchase** — `dir: 'in'`, you pay `price`, tons arrive;
- **export** — `dir: 'out'`, tons ship, money arrives;
- **pledge** — `gift: True`, tons move with no money (the token laid
  at the table).

A treaty lapses with a fax if the war comes, the treasury cannot
pay, or the stockpile cannot ship.

**Seller capacity** (`seller_capacity`) is real: a nation may only
sell what its deposits pump, less what its standing exports already
promise — and a major power keeps **half** its output at home. You
cannot buy oil from a country that has none.

### 1.5 Conquest

The fourth source, and the one the map is built around. Taking a
city transfers its deposit permanently. Ploiești is 90 oil a
fortnight; Kiev is 110 food.

---

## 2. CONSUMPTION — where tons go

### 2.1 OIL — at the pumps

Oil is **not** burned by units. Per-unit supply burn (lbs of stores)
is untouched by the resource layer — that law predates it and stands.

Instead oil is drawn at the **moment of transfer**, whenever the
supply network feeds a **machine** (`_pump`). Five call sites: depot
cache → carrier, cache → unit, carrier → unit, and two city
truck-refill paths. Plus `_pump_sortie` at each takeoff.

- **1 ton moves 1,250 lbs** of stores into a machine
  (`OIL_PER_LB = 1/1250`).
- **0.6 tons per sortie** (`OIL_PER_SORTIE`).
- **Infantry and railways draw none.** Rail legs burn no stores at
  all, so a railway is free in both stores *and* oil.

| stores issued to machines | oil |
|---|---|
| 20,000 lbs | 16 tons |
| 60,000 lbs | 48 tons |
| 150,000 lbs | 120 tons |
| 100 sorties | 60 tons |

When the stockpile is empty the transfer is **refused** — the
machine simply does not get its stores — and a throttled despatch
says so: *"PUMPS DRY — ENGINES ON RESERVE UNTIL OIL FLOWS."*
Men keep marching. This is the 1944 Wehrmacht, emergent: an army
that still has soldiers but cannot move its tanks.

### 2.2 STEEL — at the yards

`units.material_cost(unit_type)` = `cost ÷ divisor`, minimum 1:

| domain | divisor | example |
|---|---|---|
| land | 100 | Tank $430 → **4** |
| air | 80 | Fighter $460 → **5**, Bomber $620 → **7** |
| sea | 50 | Destroyer $700 → **14**, Carrier $1,950 → **39** |

**Enlisted cost no steel** — men are not built.

`_execute_budget` deducts steel as each piece is bought. If the
stockpile cannot cover the next piece, that **line halts**: it is
recorded in `bottlenecks[country]`, printed at the head of the War
Industries page, and flagged by a red pip on the factory key —
*"TIGER I PANZER LINE HALTED — WANTS 4 STEEL, HAS 3."*
The budget sheet also refuses to *plan* past the stockpile, and
prices every line in steel on the manifest.

The intended scale: a money-limited fortnight's slate costs roughly
one fortnight's mining. Steel pinches; it does not strangle.

### 2.3 FOOD — at the muster and at the table

Two draws, and this is the resource with the most reach:

**Rations for the muster** (`_ration_out`) — **4 tons a section**
(`FOOD_PER_ENLISTED`). A city raises only the men its granaries can
feed; the remainder stay on the draft roll and the fax says so:
*"12 ENLISTED MUSTER AT KIEV — 7 WAIT ON RATIONS."*
Manpower still cannot be bought — now it must be **fed**. The AI
answers to the same commissariat.

**The civil ration** (`civil_ration`) — every soul under the flag
eats, every day:

- **0.55 tons per million per day** (`CIVIL_RATION`);
- **1.6 tons per million per day** while a city is still *annexing*
  (`OCCUPIED_RATION`) — a hostile population eats dearer, so
  conquest brings **mouths** as well as factories.

| population | per day | per fortnight | if occupied |
|---|---|---|---|
| 10M | 5.5 | 77 | 16.0/day |
| 15M | 8.2 | 116 | 24.0/day |
| 30M | 16.5 | 231 | 48.0/day |

The ration is netted out inside the daily accrual, **after** income.
If it cannot be met, `_famine` fires: industry drops 0.35 points in
every town while the shortfall stands, and the Ministry of Food
reports it. Stocks never go negative.

---

## 3. THE OPENING BALANCE

Per day, at 1 September 1939 — computed from the live game:

| power | oil/day | steel/day | food/day | **food net** |
|---|---|---|---|---|
| Germany | 2.9 | 15.0 | 9.3 | **+1.2** |
| Britain | 2.9 | 12.9 | 2.9 | **−5.3** |
| USA | 15.7 | 17.1 | 30.0 | **+14.9** |
| Japan | 2.9 | 12.9 | 5.7 | **−4.9** |
| Soviet | 12.9 | 15.7 | 27.9 | **+20.6** |

Nothing in this table is scripted — it falls out of who owns which
cities, and it reproduces the strategic problems of 1939:

- **Britain** grows almost nothing (steel only) and runs **−5.3
  food a day**. She must buy her bread and ship it — the convoy war
  is an economic necessity, not flavour.
- **Japan** is short of food *and* has almost no oil (baseline
  only). Her rice and her fuel both lie in other men's colonies:
  Palembang, Saigon, Bangkok. The southern strategy writes itself.
- **Germany** feeds herself by a whisker (**+1.2**) on Königsberg
  and Munich, and has no oil of her own. Ploiești and the Ukraine
  are worth a war — because they are.
- **The Soviet Union** is the breadbasket (**+20.6**) with oil at
  Novorossiysk; **the USA** has everything and an ocean in the way.

An empty stockpile is not a wall. It is a **clock**: Britain's 260
opening tons of food last about seven weeks before the ration fails.

---

## 4. THE FOUR ANSWERS TO A SHORTAGE

1. **Buy it** — a treaty line at the table. 40 food a fortnight
   costs $280 ($210 from an ally). Prices: oil 8, food 7, steel 6
   per ton; allies pay ¾, sellers take ⅘.
2. **Take it** — capture the city and the deposit changes flag.
3. **Cut theirs** — deposits are worth nothing to an enemy who
   cannot ship; blockade and interdiction are economic weapons.
4. **Spend less** — fewer machines under way (oil), a leaner slate
   (steel), fewer musters or fewer occupied cities (food).

---

## 5. WHERE THE PLAYER READS IT

Per the UI rule that every number lives on a paper the player
already reads:

- **The resource strip** (top bar) — OIL · STEEL · FOOD, red when
  the fortnight ran negative; the hover slip itemises the flow by
  source.
- **The Quartermaster's Ledger** (resources key) — stocks, the take
  per source, spending so far, foreign sources of note, imports and
  exports by treaty, the supply-net figures, and the two plain
  rules: *one ton of oil moves 1,250 lbs into a machine*, *4 tons
  raises one section*.
- **The War Industries page** — halted lines and why.
- **The budget manifest** — every line priced in steel.
- **The negotiating table** — what a nation has to sell, and at what
  price.
- **The map** — the deposits themselves, clickable, showing output,
  owner, and what taking the city would yield.

---

## 6. CONSTANTS, IN ONE PLACE

```
RESOURCE_CAP        999          per resource, per nation
STARTING_RESOURCES  oil 400   steel 800   food 260
BASELINE_IMPORTS    oil  40   steel  60   food  40   (per fortnight)
OIL_PER_LB          1/1250       tons per lb into a machine
OIL_PER_SORTIE      0.6          tons per takeoff
FOOD_PER_ENLISTED   4            tons per section raised
CIVIL_RATION        0.55         tons per million souls per day
OCCUPIED_RATION     1.6          ditto, while annexing
TRADE_PRICES        oil 8    steel 6    food 7        ($ per ton/ftn)
TRADE_STEPS         20, 40       tonnages a treaty line may carry
BUDGET_PERIOD_DAYS  14           the fortnight
steel divisors      land 100  air 80  sea 50   (cost ÷ divisor, min 1)
```
