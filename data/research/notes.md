# Research notes: 2026 midterm ratings and polls

Pulled on 2026-11-01 (late evening PT). Most numbers were transcribed by script from Wikipedia wikitext, which cites the original raters. I did not fetch the raters' own sites, except for one search that agreed with Cook's totals (see below).

## Sources

| Data | Source | As of |
|---|---|---|
| House ratings (145 competitive seats, 10 raters) | https://en.wikipedia.org/wiki/2026_United_States_House_of_Representatives_election_ratings | Cook 10/30, Inside 10/29, Sabato 10/27, Fox 10/27; Econ, Split Ticket, DDHQ, FPO, Silver and RCP 11/1 |
| House incumbents, candidates, PVI, redistricting, specials | https://en.wikipedia.org/wiki/2026_United_States_House_of_Representatives_elections | 11/1 |
| Louisiana House rules | https://en.wikipedia.org/wiki/2026_United_States_House_of_Representatives_elections_in_Louisiana | 11/1 |
| Senate ratings (12 raters) and candidates | https://en.wikipedia.org/wiki/2026_United_States_Senate_elections | Cook 10/30, IE 10/29, Sabato 10/29, MSNOW 10/29, RCP 10/31; others 11/1 |
| Senate polls | Wikipedia "2026 United States Senate election in <State>" pages (aggregate tables: 270toWin, DDHQ, FiftyPlusOne, RCP, Silver Bulletin) | mostly 10/28 to 11/1; GA, NH, MA as of 10/20-22 |
| Generic ballot | House page aggregate table (DDHQ, FPO, NBC, RCP, Silver) | 11/1 |
| Trump approval | https://en.wikipedia.org/wiki/Opinion_polling_on_the_second_Trump_presidency | 11/1 |
| Cross-check | Search results for cookpolitical.com: Cook "Four Days Out, a Dozen More House Races Move Toward Democrats" (about 10/30) says 18 toss-ups and a D gain of 12-25 seats, with FL-25 moving to Lean D. This matches the Wikipedia data. | ~10/30 |

## How to read the files

- `house_ratings.csv` has all 435 districts with 2026 numbering. All 10 raters are listed only for the 145 seats on Wikipedia's competitive list. Wikipedia defines that list as seats that at least one rater calls non-Safe. The other 289 seats have `other_source=implied`. For those, I filled cook/inside/sabato with "Safe X" from the district PVI and the candidates. These are **derived, not published per-seat ratings**. CA-01 is left blank because the seat is D+7 but held by an R, and it is not on the list.
- `other_rating` holds the rest of the raters as `Name=Rating` pairs, separated by semicolons. Solid is mapped to Safe. The Economist's "Likely" and "Very Likely" are mapped to Lean and Likely by Wikipedia's convention.
- `senate_polls.csv` has one row per aggregator plus an "Average" row for 20 races. For 10 races with no aggregate, it has the last 1-3 single polls. The margin is (D, or the lead non-R) minus R. For NE, ID and SD, the lead non-R is an independent. For MT it is the independent Bodnar, and the Democrat's share is in the notes.

## Surprising findings

1. **A large Democratic wave is signaled.** The generic ballot is D+8.7. Trump approval averages 36.8/60.5 (net -23.7). Every House rater has Democrats past 218, from 222 (Cook) to 230 (Econ, FPO, Silver).
2. **Republicans are on defense in the Senate in red states.** KS is a toss-up, with Hamilton (D) +2.8 over Sen. Marshall. TX has Talarico (D) +3.3 over Paxton, who beat Cornyn in the primary. OH has Brown +2.6. AK has Peltola +1.9. IA is tied (Turek +0.1). In ME, Jackson leads Collins by 4.1. In NC, Cooper leads by 10.7.
3. **SC is close after Lindsey Graham's death (July 11, 2026).** Darline Graham (R) leads Andrews (D) by only 1.4 in an R+8 state.
4. **NE (Osborn, I) trails by 1.6. LA has a D internal poll tied at 45-45.** MS polls are all D internals (R +3 to +6).
5. **Redistricting cuts both ways.** Texas made 5 new R seats. California's Prop 50 made about 4 D gains. After Louisiana v. Callais (April 2026), AL, LA and TN each removed a D or Black-majority seat. FL redrew (+3 R). MO and VA maps were blocked, so the old maps stay. Even so, the R-drawn seats are now competitive in a D+9 environment: TX-15, TX-35, FL-07, FL-09 and FL-14 are all rated.
6. **Raters disagree most on these seats.** Models are more D-leaning than handicappers in CA-22, MI-07, NY-17, FL-14, NC-01 and PA-01. Handicappers are more D-leaning than models in CO-05 and TX-35. For ME-02, Cook, IE and Sabato say Lean R while most models say Toss-up. For MO-02, Sabato says Toss-up while IE says Safe R. 40 rated seats span 3 or more steps across the 10 raters.
7. **The special elections were D overperformances.** GA-14 (about R+37) was held by Fuller (R) by only 55.9-44.1. NJ-11 went D 60.2-39.4.
8. **Louisiana House runs a jungle primary on Nov 3, with a Dec 12 runoff.** The calendar changed after redistricting.

## Caveats

- Wikipedia is crowd-edited. Small transcription errors are possible. The OK-SEN Democratic nominee's name is inconsistent on Wikipedia.
- Many Senate aggregates mix partisan internal polls.
- Polling-error history: polls underestimated the GOP in 2016, 2020 and 2024. Midterm polling in 2018 and 2022 was close. This comes from general knowledge, not a source pulled this session.
