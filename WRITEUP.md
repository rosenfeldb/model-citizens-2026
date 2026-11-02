# Write-up

We treat this contest as two problems: estimating each race, then choosing picks that give us the best
chance to finish first. Our probabilities blend Kalshi's Nov 1 prices (de-biased for the favorite-longshot
bias), the average of ten expert and model ratings mapped to their historical hit rates, and Senate polling
averages. We left out fundraising, demographics, and our own fundamentals regression: prices and ratings
already absorb them, and extra inputs added noise. The scoring rule pays `-log2(p)` for a correct pick, so
underdogs carry most of the value, and a national polling miss moves dozens of races together. We built a
Gaussian factor simulator (national, regional, state, and Hispanic-voter swings) that keeps each race's
probability but adds realistic co-movement, simulated fields of 10–100 rival entrants with different
habits, and optimized our 470 picks to maximize P(winning) over 20,000 simulated elections, checked on a
fresh 20,000. The optimizer's lesson: rivals who chase underdogs on both sides crowd the "Democrats beat
the polls" scenarios, so the open lane is the opposite one. We back the Republican in D-leaning races
where the model gives them a real (≥3%) chance, and keep favorites elsewhere. Against 30 simulated rivals
this wins about 26% of the time versus 0.5% for picking favorites, and stays ahead of an expected-points
strategy under four of five alternative "truths." Risks: it is a one-direction bet that does poorly if
Democrats beat their polls; we do not know the real field; Kalshi's tail calibration rests on only 42
races from 2024; and expert ratings may lag a wave.
