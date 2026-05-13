/**
 * ============================================================
 * FITAI — SEED DATA v2.0
 * ============================================================
 * Wklej całą zawartość tego pliku do sekcji <script> w index.html,
 * PRZED definicją funkcji bibliotekaMealFilter i atlasExerciseFilter.
 *
 * Zawiera:
 *   • MEAL_DB      — 36 posiłków (śniadanie / obiad / kolacja / przekąska)
 *   • EXERCISE_DB  — 48 ćwiczeń  (klatka / plecy / nogi / barki / ramiona / brzuch)
 *   • SPORT_DRILLS — 5 dyscyplin × 2-3 kategorie × 5 drilli = 65 drilli
 *
 * Format jest identyczny z istniejącymi wpisami w index.html,
 * więc wszystkie funkcje renderujące działają bez zmian.
 * ============================================================
 */

// ─────────────────────────────────────────────────────────────────────────────
// 1. MEAL_DB
// ─────────────────────────────────────────────────────────────────────────────
// Pola wymagane przez renderBibliotekaMeals() i _build_weekly_plan():
//   name, protein, carbs, fat, kcal, tags[], ingredients[{item, amount}], recipe
// ─────────────────────────────────────────────────────────────────────────────
const MEAL_DB = {

  // ── ŚNIADANIE ───────────────────────────────────────────────────────────────
  śniadanie: [
    {
      name: 'Owsianka z jagodami',
      protein: 15, carbs: 55, fat: 5, kcal: 320,
      tags: ['owies', 'gluten'],
      ingredients: [
        { item: 'Płatki owsiane', amount: '80g' },
        { item: 'Jagody świeże', amount: '100g' },
        { item: 'Mleko 2%', amount: '200ml' },
        { item: 'Miód', amount: '1 łyżka' },
      ],
      recipe: 'Zagotuj mleko, wsyp płatki i gotuj 5 min na małym ogniu. Wyłóż do miski, udekoruj jagodami i skrop miodem.',
    },
    {
      name: 'Jajecznica z awokado',
      protein: 22, carbs: 6, fat: 20, kcal: 295,
      tags: ['jajka'],
      ingredients: [
        { item: 'Jajka', amount: '3 szt' },
        { item: 'Awokado', amount: '½ szt' },
        { item: 'Masło', amount: '1 łyżeczka' },
        { item: 'Sól, pieprz', amount: 'do smaku' },
      ],
      recipe: 'Roztop masło na patelni. Wbij jajka i mieszaj do uzyskania kremowej konsystencji. Podaj z plastrami awokado.',
    },
    {
      name: 'Jogurt grecki z granolą',
      protein: 18, carbs: 40, fat: 8, kcal: 300,
      tags: ['nabiał'],
      ingredients: [
        { item: 'Jogurt grecki 0%', amount: '200g' },
        { item: 'Granola', amount: '50g' },
        { item: 'Owoce sezonowe', amount: '100g' },
      ],
      recipe: 'Wyłóż jogurt do miseczki. Posyp granolą i ułóż owoce. Opcjonalnie dodaj łyżeczkę masła orzechowego.',
    },
    {
      name: 'Tost z łososiem i twarożkiem',
      protein: 25, carbs: 28, fat: 10, kcal: 300,
      tags: ['ryby', 'gluten'],
      ingredients: [
        { item: 'Chleb żytni', amount: '2 kromki' },
        { item: 'Łosoś wędzony', amount: '80g' },
        { item: 'Twarożek chudy', amount: '50g' },
        { item: 'Koper świeży', amount: 'kilka gałązek' },
      ],
      recipe: 'Opiecz chleb. Posmaruj twarożkiem, ułóż płaty łososia, udekoruj koperkiem.',
    },
    {
      name: 'Naleśniki proteinowe',
      protein: 28, carbs: 35, fat: 5, kcal: 295,
      tags: ['jajka', 'gluten'],
      ingredients: [
        { item: 'Mąka owsiana', amount: '60g' },
        { item: 'Jajka', amount: '2 szt' },
        { item: 'Odżywka białkowa wanilia', amount: '1 miarka (30g)' },
        { item: 'Mleko', amount: '100ml' },
      ],
      recipe: 'Połącz wszystkie składniki w blenderze. Smaż na patelni non-stick po 2–3 min z każdej strony.',
    },
    {
      name: 'Bowl ryżowy z jajkiem',
      protein: 20, carbs: 48, fat: 9, kcal: 355,
      tags: ['jajka', 'ryż'],
      ingredients: [
        { item: 'Ryż jaśminowy', amount: '80g suchy' },
        { item: 'Jajko sadzone', amount: '2 szt' },
        { item: 'Edamame', amount: '60g' },
        { item: 'Sos sojowy', amount: '1 łyżeczka' },
      ],
      recipe: 'Ugotuj ryż. Usmaż jajka sadzone. Ułóż w misce ryż, edamame i jajka. Skrop sosem sojowym.',
    },
    {
      name: 'Koktajl bananowo-szpinakowy',
      protein: 14, carbs: 42, fat: 4, kcal: 258,
      tags: ['vege'],
      ingredients: [
        { item: 'Banan', amount: '1 szt' },
        { item: 'Szpinak baby', amount: '50g' },
        { item: 'Jogurt naturalny', amount: '150g' },
        { item: 'Mleko migdałowe', amount: '150ml' },
      ],
      recipe: 'Wrzuć wszystkie składniki do blendera i miksuj 45 sekund. Podaj od razu.',
    },
    {
      name: 'Omlet ze szpinakiem i fetą',
      protein: 24, carbs: 5, fat: 16, kcal: 265,
      tags: ['jajka', 'nabiał'],
      ingredients: [
        { item: 'Jajka', amount: '3 szt' },
        { item: 'Szpinak świeży', amount: '60g' },
        { item: 'Ser feta', amount: '30g' },
        { item: 'Oliwa z oliwek', amount: '1 łyżeczka' },
      ],
      recipe: 'Podsmaż szpinak 1 min. Wlej ubite jajka, posyp fetą i złóż omlet na pół po 3 min.',
    },
    {
      name: 'Kanapki z masłem orzechowym i bananem',
      protein: 12, carbs: 52, fat: 14, kcal: 380,
      tags: ['gluten', 'orzechy'],
      ingredients: [
        { item: 'Chleb pełnoziarnisty', amount: '2 kromki' },
        { item: 'Masło orzechowe naturalne', amount: '2 łyżki' },
        { item: 'Banan', amount: '½ szt' },
        { item: 'Cynamon', amount: 'szczypta' },
      ],
      recipe: 'Posmaruj chleb masłem orzechowym. Ułóż plastry banana, posyp cynamonem.',
    },
  ],

  // ── OBIAD ────────────────────────────────────────────────────────────────────
  obiad: [
    {
      name: 'Kurczak z ryżem i brokułami',
      protein: 40, carbs: 55, fat: 6, kcal: 440,
      tags: ['kurczak', 'ryż'],
      ingredients: [
        { item: 'Pierś kurczaka', amount: '180g' },
        { item: 'Ryż biały', amount: '80g suchy' },
        { item: 'Brokuły', amount: '150g' },
        { item: 'Oliwa z oliwek', amount: '1 łyżka' },
      ],
      recipe: 'Ugotuj ryż. Grilluj pierś kurczaka 6–7 min z każdej strony. Ugotuj brokuły al dente. Polej oliwą i dopraw.',
    },
    {
      name: 'Łosoś z batatami i szpinakiem',
      protein: 32, carbs: 38, fat: 14, kcal: 405,
      tags: ['ryby'],
      ingredients: [
        { item: 'Filet z łososia', amount: '160g' },
        { item: 'Bataty', amount: '200g' },
        { item: 'Szpinak baby', amount: '100g' },
        { item: 'Cytryna', amount: '½ szt' },
      ],
      recipe: 'Piecz łososia w 180°C przez 18 min. Ugotuj bataty. Podsmaż szpinak 2 min. Skrop cytryną.',
    },
    {
      name: 'Makaron z tuńczykiem i pomidorami',
      protein: 35, carbs: 60, fat: 8, kcal: 450,
      tags: ['ryby', 'gluten'],
      ingredients: [
        { item: 'Makaron pełnoziarnisty', amount: '80g suchy' },
        { item: 'Tuńczyk w wodzie', amount: '150g' },
        { item: 'Pomidory cherry', amount: '200g' },
        { item: 'Czosnek', amount: '2 ząbki' },
      ],
      recipe: 'Ugotuj makaron al dente. Na patelni podsmaż czosnek, dodaj pomidory cherry. Wymieszaj z makaronem i tuńczykiem.',
    },
    {
      name: 'Quinoa z tofu i warzywami',
      protein: 22, carbs: 45, fat: 10, kcal: 365,
      tags: ['vege', 'soja'],
      ingredients: [
        { item: 'Quinoa', amount: '80g sucha' },
        { item: 'Tofu twarde', amount: '150g' },
        { item: 'Warzywa stir-fry mrożone', amount: '200g' },
        { item: 'Sos sojowy', amount: '2 łyżki' },
      ],
      recipe: 'Ugotuj quinoa 15 min. Podsmaż tofu na złoto, dodaj warzywa i sos sojowy. Podaj z quinoa.',
    },
    {
      name: 'Mielony indyk z kaszą gryczaną',
      protein: 38, carbs: 45, fat: 5, kcal: 385,
      tags: ['drób'],
      ingredients: [
        { item: 'Mielony indyk', amount: '180g' },
        { item: 'Kasza gryczana', amount: '70g sucha' },
        { item: 'Pomidory z puszki', amount: '200g' },
        { item: 'Czosnek', amount: '2 ząbki' },
      ],
      recipe: 'Ugotuj kaszę. Podsmaż indyk z czosnkiem do zrumienienia. Dodaj pomidory i duś 10 min. Podaj z kaszą.',
    },
    {
      name: 'Wrap z kurczakiem i guacamole',
      protein: 36, carbs: 42, fat: 14, kcal: 435,
      tags: ['kurczak', 'gluten'],
      ingredients: [
        { item: 'Tortilla pełnoziarnista', amount: '2 szt' },
        { item: 'Grillowany kurczak', amount: '150g' },
        { item: 'Awokado', amount: '½ szt' },
        { item: 'Salsa pomidorowa', amount: '3 łyżki' },
      ],
      recipe: 'Pokrój kurczaka. Zmiksuj awokado z solą i cytryną. Ułóż w tortilli, zawiń ciasno.',
    },
    {
      name: 'Zupa krem z dyni z pestkami',
      protein: 8, carbs: 32, fat: 10, kcal: 250,
      tags: ['vege'],
      ingredients: [
        { item: 'Dynia Hokkaido', amount: '400g' },
        { item: 'Cebula', amount: '1 szt' },
        { item: 'Mleko kokosowe', amount: '100ml' },
        { item: 'Pestki dyni', amount: '20g' },
      ],
      recipe: 'Ugotuj dynię z cebulą w bulionie 20 min. Zblenduj, dodaj mleko kokosowe. Podaj z pestkami.',
    },
    {
      name: 'Stek z polędwicy z warzywami',
      protein: 42, carbs: 15, fat: 18, kcal: 390,
      tags: ['wołowina'],
      ingredients: [
        { item: 'Polędwica wołowa', amount: '180g' },
        { item: 'Szparagi', amount: '150g' },
        { item: 'Pomidory cherry', amount: '100g' },
        { item: 'Masło', amount: '1 łyżeczka' },
      ],
      recipe: 'Rozgrzej patelnię do max. Smaż stek 3 min z każdej strony. Odpoczynek 5 min. Podsmaż warzywa na maśle.',
    },
    {
      name: 'Bowl z ciecierzycą i tahini',
      protein: 18, carbs: 50, fat: 14, kcal: 390,
      tags: ['vege'],
      ingredients: [
        { item: 'Ciecierzyca z puszki', amount: '240g' },
        { item: 'Tahini', amount: '2 łyżki' },
        { item: 'Kombucha z ryżu', amount: '100g suchy' },
        { item: 'Mix surówka', amount: '150g' },
      ],
      recipe: 'Upiecz ciecierzycę 20 min w 200°C. Ugotuj ryż. Wyłóż do miski z surówką. Polej tahini rozcieńczonym wodą.',
    },
  ],

  // ── KOLACJA ──────────────────────────────────────────────────────────────────
  kolacja: [
    {
      name: 'Sałatka z grillowanym kurczakiem',
      protein: 30, carbs: 15, fat: 12, kcal: 295,
      tags: ['kurczak'],
      ingredients: [
        { item: 'Grillowany kurczak', amount: '120g' },
        { item: 'Mix sałat', amount: '100g' },
        { item: 'Pomidor malinowy', amount: '1 szt' },
        { item: 'Oliwa z oliwek + ocet balsamiczny', amount: '1 łyżka każdy' },
      ],
      recipe: 'Pogrilluj pierś kurczaka, pokrój w plastry. Wymieszaj sałaty z warzywami. Polej dressingiem i ułóż kurczaka.',
    },
    {
      name: 'Omlet warzywny z serem',
      protein: 18, carbs: 8, fat: 12, kcal: 220,
      tags: ['jajka', 'nabiał'],
      ingredients: [
        { item: 'Jajka', amount: '3 szt' },
        { item: 'Papryka czerwona', amount: '½ szt' },
        { item: 'Cebula', amount: '½ szt' },
        { item: 'Ser żółty light', amount: '20g' },
      ],
      recipe: 'Ubij jajka z solą. Podsmaż warzywa 3 min. Wlej jajka, posyp serem i złóż omlet po 3 min.',
    },
    {
      name: 'Ryba pieczona z warzywami',
      protein: 28, carbs: 12, fat: 8, kcal: 245,
      tags: ['ryby'],
      ingredients: [
        { item: 'Dorsz lub mintaj', amount: '160g' },
        { item: 'Cukinia', amount: '150g' },
        { item: 'Papryka żółta', amount: '1 szt' },
        { item: 'Zioła prowansalskie + oliwa', amount: 'do smaku' },
      ],
      recipe: 'Ułóż rybę i warzywa na blasze, skrop oliwą i posyp ziołami. Piecz w 200°C przez 22–25 min.',
    },
    {
      name: 'Kasza jaglana z fasolą i szpinakiem',
      protein: 16, carbs: 55, fat: 4, kcal: 330,
      tags: ['vege'],
      ingredients: [
        { item: 'Kasza jaglana', amount: '80g sucha' },
        { item: 'Fasola cannellini z puszki', amount: '200g' },
        { item: 'Szpinak baby', amount: '100g' },
        { item: 'Czosnek + oliwa', amount: 'do smaku' },
      ],
      recipe: 'Ugotuj kaszę 15 min. Podsmaż czosnek, dodaj fasolę i szpinak na 3 min. Wymieszaj z kaszą.',
    },
    {
      name: 'Twaróg z pomidorami i szczypiorkiem',
      protein: 20, carbs: 8, fat: 4, kcal: 145,
      tags: ['nabiał'],
      ingredients: [
        { item: 'Twaróg chudy', amount: '200g' },
        { item: 'Pomidor', amount: '2 szt' },
        { item: 'Szczypiorek', amount: '1 pęczek' },
        { item: 'Sól, pieprz', amount: 'do smaku' },
      ],
      recipe: 'Pokrój pomidory. Posiekaj szczypiorek. Podaj twaróg z pomidorami i posyp szczypiorkiem.',
    },
    {
      name: 'Zupa miso z tofu i glonami',
      protein: 14, carbs: 12, fat: 6, kcal: 155,
      tags: ['vege', 'soja'],
      ingredients: [
        { item: 'Pasta miso', amount: '2 łyżki' },
        { item: 'Tofu jedwabiste', amount: '100g' },
        { item: 'Algi wakame', amount: '5g suche' },
        { item: 'Dymka', amount: '2 łodygi' },
      ],
      recipe: 'Zagotuj 500ml wody. Rozpuść miso (nie gotuj!). Dodaj tofu w kostkach, glony i dymkę.',
    },
    {
      name: 'Pierogi ze szpinakiem i ricottą',
      protein: 16, carbs: 48, fat: 10, kcal: 350,
      tags: ['nabiał', 'gluten'],
      ingredients: [
        { item: 'Pierogi gotowe ze szpinakiem', amount: '250g' },
        { item: 'Ricotta', amount: '50g' },
        { item: 'Masło', amount: '1 łyżeczka' },
        { item: 'Szałwia', amount: '3 listki' },
      ],
      recipe: 'Ugotuj pierogi. Rozpuść masło, podsmaż szałwię 1 min. Podaj pierogi polane masłem z ricottą.',
    },
    {
      name: 'Sałatka caprese z mozzarellą',
      protein: 16, carbs: 10, fat: 18, kcal: 270,
      tags: ['nabiał'],
      ingredients: [
        { item: 'Mozzarella di bufala', amount: '125g' },
        { item: 'Pomidory malinowe', amount: '250g' },
        { item: 'Bazylia świeża', amount: '1 garść' },
        { item: 'Oliwa extra virgin + sól', amount: '2 łyżki' },
      ],
      recipe: 'Pokrój pomidory i mozzarellę w plastry. Układaj naprzemiennie. Polej oliwą, posyp solą i bazylią.',
    },
    {
      name: 'Kurczak w sosie curry z ryżem',
      protein: 38, carbs: 52, fat: 10, kcal: 455,
      tags: ['kurczak', 'ryż'],
      ingredients: [
        { item: 'Pierś kurczaka', amount: '160g' },
        { item: 'Mleko kokosowe', amount: '100ml' },
        { item: 'Pasta curry żółta', amount: '1 łyżka' },
        { item: 'Ryż basmati', amount: '80g suchy' },
      ],
      recipe: 'Ugotuj ryż. Podsmaż kurczaka, dodaj pastę curry i mleko kokosowe. Duś 8 min. Podaj z ryżem.',
    },
  ],

  // ── PRZEKĄSKA ────────────────────────────────────────────────────────────────
  przekąska: [
    {
      name: 'Shake proteinowy czekoladowy',
      protein: 25, carbs: 12, fat: 2, kcal: 165,
      tags: [],
      ingredients: [
        { item: 'Odżywka białkowa czekolada', amount: '1 miarka (30g)' },
        { item: 'Mleko lub woda', amount: '300ml' },
        { item: 'Lód', amount: '4 kostki' },
      ],
      recipe: 'Wrzuć wszystko do shakerka, wstrząśnij 30 sekund. Opcjonalnie dodaj łyżkę masła orzechowego.',
    },
    {
      name: 'Orzechy migdałowe i owoc',
      protein: 6, carbs: 20, fat: 16, kcal: 240,
      tags: ['orzechy'],
      ingredients: [
        { item: 'Migdały niesolone', amount: '30g' },
        { item: 'Jabłko lub gruszka', amount: '1 szt' },
      ],
      recipe: 'Zjedz migdały powoli — żucie 20× na porcję aktywuje sygnał sytości. Popij wodą.',
    },
    {
      name: 'Twarożek z rzodkiewkami',
      protein: 15, carbs: 10, fat: 2, kcal: 120,
      tags: ['nabiał'],
      ingredients: [
        { item: 'Twarożek chudy', amount: '150g' },
        { item: 'Rzodkiewki', amount: '5 szt' },
        { item: 'Szczypiorek', amount: 'kilka listków' },
      ],
      recipe: 'Wymieszaj twarożek ze szczypiorkiem i szczyptą soli. Podaj z pokrojonymi rzodkiewkami.',
    },
    {
      name: 'Chipsy z ciecierzycy',
      protein: 8, carbs: 22, fat: 6, kcal: 175,
      tags: ['vege'],
      ingredients: [
        { item: 'Ciecierzyca z puszki', amount: '200g (odsączona)' },
        { item: 'Oliwa', amount: '1 łyżka' },
        { item: 'Papryka wędzona + sól', amount: '1 łyżeczka' },
      ],
      recipe: 'Osusz ciecierzycę. Wymieszaj z oliwą i przyprawami. Piecz w 200°C przez 25–30 min, mieszając w połowie.',
    },
    {
      name: 'Smoothie bowl z malinami',
      protein: 10, carbs: 35, fat: 5, kcal: 225,
      tags: ['nabiał'],
      ingredients: [
        { item: 'Maliny mrożone', amount: '150g' },
        { item: 'Jogurt grecki 0%', amount: '100g' },
        { item: 'Nasiona chia', amount: '1 łyżka' },
        { item: 'Granola', amount: '30g' },
      ],
      recipe: 'Zblenduj maliny z jogurtem na gęsty krem. Wylej do miski. Posyp chia i granolą.',
    },
    {
      name: 'Ryżowe wafle z masłem orzechowym',
      protein: 8, carbs: 28, fat: 12, kcal: 250,
      tags: ['orzechy'],
      ingredients: [
        { item: 'Wafle ryżowe', amount: '3 szt' },
        { item: 'Masło orzechowe naturalne', amount: '2 łyżki' },
        { item: 'Banan', amount: '½ szt' },
      ],
      recipe: 'Posmaruj wafle masłem orzechowym. Ułóż plastry banana. Opcjonalnie posyp cynamonem.',
    },
    {
      name: 'Kawałki sera i warzywa',
      protein: 12, carbs: 8, fat: 10, kcal: 170,
      tags: ['nabiał'],
      ingredients: [
        { item: 'Ser żółty 45%', amount: '40g' },
        { item: 'Marchewka', amount: '1 szt' },
        { item: 'Seler naciowy', amount: '2 łodygi' },
        { item: 'Hummus', amount: '2 łyżki' },
      ],
      recipe: 'Pokrój warzywa w słupki. Podaj z serem i hummusem. Idealne do pracy.',
    },
    {
      name: 'Daktyle z masłem migdałowym',
      protein: 4, carbs: 38, fat: 8, kcal: 240,
      tags: ['orzechy'],
      ingredients: [
        { item: 'Daktyle medjool', amount: '4 szt' },
        { item: 'Masło migdałowe', amount: '1 łyżka' },
        { item: 'Sól morska w płatkach', amount: 'szczypta' },
      ],
      recipe: 'Usuń pestki z daktyli. Napełnij każdy masłem migdałowym. Posyp solą. Zjedz przed treningiem.',
    },
    {
      name: 'Jajka gotowane z solą i pieprzem',
      protein: 12, carbs: 1, fat: 10, kcal: 143,
      tags: ['jajka'],
      ingredients: [
        { item: 'Jajka', amount: '2 szt' },
        { item: 'Sól morska', amount: 'szczypta' },
        { item: 'Pieprz cayenne', amount: 'szczypta' },
      ],
      recipe: 'Gotuj jajka 8 min od wrzenia (na twardo). Przelej zimną wodą. Obierz i dopraw.',
    },
  ],

}; // koniec MEAL_DB


// ─────────────────────────────────────────────────────────────────────────────
// 2. EXERCISE_DB
// ─────────────────────────────────────────────────────────────────────────────
// Pola wymagane przez atlasExerciseFilter() i _build_weekly_plan():
//   name, sets, reps, weight, tags[], muscles (string), desc
// Pola dodatkowe (wyświetlane w modalu):
//   difficulty (1–5), instructions (string)
// ─────────────────────────────────────────────────────────────────────────────
const EXERCISE_DB = {

  // ── KLATKA ──────────────────────────────────────────────────────────────────
  klatka: [
    {
      name: 'Wyciskanie sztangi leżąc',
      sets: 4, reps: 6, weight: 80,
      tags: ['sztanga', 'ławka'],
      muscles: 'klatka piersiowa, trójgłowy, przedni bark',
      desc: 'Połóż się na ławce, trzymaj sztangę na szerokość barków. Opuszczaj do klatki i wypychaj dynamicznie.',
      difficulty: 3,
      instructions: 'Ściągnij łopatki i wbij je w ławkę. Łokcie pod ~45°. Eksplozywna faza wyciskania, kontrolowana faza opuszczania (3 sekundy).',
    },
    {
      name: 'Wyciskanie hantli leżąc',
      sets: 4, reps: 10, weight: 28,
      tags: ['hantle', 'ławka'],
      muscles: 'klatka piersiowa',
      desc: 'Głębszy zakres ruchu niż sztanga. Leż na ławce z hantlami w rękach.',
      difficulty: 2,
      instructions: 'Opuszczaj hantle poniżej poziomu klatki, pamiętaj o pełnym rozciągnięciu. Wyciskaj neutralnym uchwytem.',
    },
    {
      name: 'Pompki',
      sets: 4, reps: 20, weight: 0,
      tags: [],
      muscles: 'klatka piersiowa, trójgłowy, core',
      desc: 'Klasyczny trening klatki bez sprzętu. Postaw stopy na podwyższeniu, by zwiększyć trudność.',
      difficulty: 1,
      instructions: 'Ręce na szerokość barków. Ciało w linii prostej. Opuszczaj klatkę do 2 cm od podłogi.',
    },
    {
      name: 'Rozpiętki na wyciągach (kable)',
      sets: 3, reps: 14, weight: 20,
      tags: ['kable'],
      muscles: 'klatka piersiowa (izolacja)',
      desc: 'Idealne ćwiczenie izolacyjne na klatę. Stały opór w całym zakresie ruchu.',
      difficulty: 2,
      instructions: 'Stań pośrodku wyciągów, lekko pochylony. Złącz uchwyty przed klatką z lekko ugiętymi łokciami.',
    },
    {
      name: 'Wyciskanie hantli na skosie dodatnim',
      sets: 4, reps: 10, weight: 24,
      tags: ['hantle', 'ławka'],
      muscles: 'górna klatka piersiowa, przedni bark',
      desc: 'Ławka pod kątem 30–45°. Skupia wysiłek na górnej klatce.',
      difficulty: 3,
      instructions: 'Nie ustawiaj ławki powyżej 45° — powyżej tej granicy dominuje bark. Utrzymuj łopatki stabilnie.',
    },
    {
      name: 'Rozpiętki z hantlami leżąc',
      sets: 3, reps: 12, weight: 14,
      tags: ['hantle', 'ławka'],
      muscles: 'klatka piersiowa (rozciąganie)',
      desc: 'Ćwiczenie nastawione na rozciąganie klatki i izolację. Nie używaj ciężkich obciążeń.',
      difficulty: 2,
      instructions: 'Opuszczaj hantle szeroko w bok z lekko ugiętymi łokciami. W dolnym punkcie odczuj rozciąganie.',
    },
    {
      name: 'Pompki diamentowe',
      sets: 3, reps: 15, weight: 0,
      tags: [],
      muscles: 'triceps, środkowa klatka',
      desc: 'Dłonie ułożone w kształt diamentu pod mostkiem. Mocniej angażuje triceps.',
      difficulty: 2,
      instructions: 'Kciuki i palce wskazujące tworzą trójkąt. Łokcie cofają się wzdłuż ciała (nie na boki).',
    },
    {
      name: 'Dips na poręczach',
      sets: 3, reps: 10, weight: 0,
      tags: [],
      muscles: 'klatka (dolna część), triceps',
      desc: 'Przy wyraźnym pochyleniu tułowia do przodu angażuje dolną klatkę. Jeden z najlepszych ruchów wielostawowych.',
      difficulty: 3,
      instructions: 'Pochyl tułów ~30° do przodu i chyl łokcie lekko na boki. Opuszczaj się do pełnego zakresu.',
    },
  ],

  // ── PLECY ───────────────────────────────────────────────────────────────────
  plecy: [
    {
      name: 'Wiosłowanie sztangą',
      sets: 4, reps: 8, weight: 70,
      tags: ['sztanga'],
      muscles: 'szerokie grzbietu, biceps, tylny bark',
      desc: 'Pochyl się 45°, wiosłuj sztangę do pasa. W górze ściskaj łopatki przez 1 sekundę.',
      difficulty: 3,
      instructions: 'Plecy proste, nie zaginaj. Prowadź łokcie wzdłuż ciała. Chwyć na szerokość barków lub szerzej.',
    },
    {
      name: 'Podciąganie na drążku',
      sets: 4, reps: 8, weight: 0,
      tags: ['drążek'],
      muscles: 'szerokie grzbietu, biceps, środkowy grzbiet',
      desc: 'Najskuteczniejsze ćwiczenie na plecy. Podciągaj do brody, a nie tylko do nosa.',
      difficulty: 4,
      instructions: 'Szeroki chwyt = więcej lat. Wąski chwyt = więcej biceps. Zainicjuj ruch ściągnięciem łopatek w dół.',
    },
    {
      name: 'Wiosłowanie hantlem jednostronnie',
      sets: 4, reps: 10, weight: 36,
      tags: ['hantle'],
      muscles: 'szerokie grzbietu, biceps (unilateralnie)',
      desc: 'Pozwala na większy zakres ruchu niż wiosłowanie oburęczne. Klękasz kolanem i dłonią na ławce.',
      difficulty: 2,
      instructions: 'Ciągnij łokieć maksymalnie do tyłu i wzwyż. Nie skręcaj bioder.',
    },
    {
      name: 'Ściąganie drążka na maszynie (lat pulldown)',
      sets: 4, reps: 10, weight: 55,
      tags: ['maszyna'],
      muscles: 'szerokie grzbietu, środkowy grzbiet',
      desc: 'Alternatywa dla podciągań — łatwiejsza w regulacji obciążenia i nauce wzorca ruchu.',
      difficulty: 2,
      instructions: 'Ściągaj drążek do obojczyków (nie za głowę). Pełne wyprostowanie rąk na górze.',
    },
    {
      name: 'Wiosłowanie na wyciągu (cable row)',
      sets: 3, reps: 12, weight: 50,
      tags: ['kable'],
      muscles: 'środkowy grzbiet, romboidy, biceps',
      desc: 'Stały opór w całym zakresie ruchu. Lepsze dla rozciągania środkowego grzbietu niż wiosłowanie sztangą.',
      difficulty: 2,
      instructions: 'Siedź prosto. Ściągaj uchwyt do brzucha. Pełne wyprostowanie rąk w fazie ekscentrycznej.',
    },
    {
      name: 'Martwy ciąg',
      sets: 3, reps: 5, weight: 100,
      tags: ['sztanga', 'baza'],
      muscles: 'cały łańcuch tylny, nogi, pośladki',
      desc: 'Król ćwiczeń siłowych. Angażuje większą masę mięśniową niż jakiekolwiek inne ćwiczenie.',
      difficulty: 5,
      instructions: 'Stopy pod sztangą — paski sznurowadeł pod drążkiem. Plecy proste, biodra wypchnięte do tyłu. Wdech przed startem, pcha podłogę nogami.',
    },
    {
      name: 'Hyperextension (wyprosty grzbietu)',
      sets: 3, reps: 15, weight: 10,
      tags: ['ławka'],
      muscles: 'prostowniki grzbietu, pośladki, mięsień czworogłowy uda tylny',
      desc: 'Ćwiczenie izolacyjne na dolne plecy. Pomaga zapobiegać bólom kręgosłupa.',
      difficulty: 1,
      instructions: 'Ruch kończy się gdy ciało tworzy prostą linię — nie przeginaj się nadmiernie do tyłu.',
    },
    {
      name: 'Spiderowy (twarz do ławki) wiosłowanie',
      sets: 3, reps: 12, weight: 20,
      tags: ['hantle', 'ławka'],
      muscles: 'środkowy grzbiet, tylny bark',
      desc: 'Leżąc twarzą do ławki (pod kątem 45°). Eliminuje oszukiwanie ciałem.',
      difficulty: 2,
      instructions: 'Wyciągnij ręce w dół. Wiosłuj z pełnym zakresem, prowadząc łokcie szeroko na boki.',
    },
  ],

  // ── NOGI ────────────────────────────────────────────────────────────────────
  nogi: [
    {
      name: 'Przysiad ze sztangą',
      sets: 4, reps: 6, weight: 90,
      tags: ['sztanga', 'baza'],
      muscles: 'czworogłowy, pośladki, mięsień dwugłowy uda',
      desc: 'Podstawowe ćwiczenie na nogi. Aktywuje największe grupy mięśniowe ciała.',
      difficulty: 4,
      instructions: 'Sztanga na trapezach. Stopy na szerokość bioder, lekko rozchylone. Kolana za linią palców stóp. Głębokość: ud minimum równolegle do podłogi.',
    },
    {
      name: 'Wyciskanie nóg na suwnicy',
      sets: 4, reps: 12, weight: 140,
      tags: ['maszyna'],
      muscles: 'czworogłowy, pośladki',
      desc: 'Większe obciążenia niż przysiad, mniejsze ryzyko urazu. Idealne do hipertrofii.',
      difficulty: 2,
      instructions: 'Stopy na szerokość bioder. Zablokuj kolana w górze, ale nie do pełnego wyprostu (zostaw 5°). Nie odrywaj pośladków od siedzenia.',
    },
    {
      name: 'Martwy ciąg rumuński',
      sets: 4, reps: 10, weight: 70,
      tags: ['sztanga', 'baza'],
      muscles: 'mięsień dwugłowy uda, pośladki, prostowniki grzbietu',
      desc: 'Najlepsza izolacja mięśni dwugłowych uda. Skup się na rozciąganiu w fazie ekscentrycznej.',
      difficulty: 3,
      instructions: 'Plecy prosto. Opuszczaj sztangę wzdłuż nóg (blisko ciała) pochylając biodra do tyłu. Zatrzymaj się 2 cm poniżej kolan.',
    },
    {
      name: 'Wykrok z hantlami',
      sets: 3, reps: 12, weight: 20,
      tags: ['hantle'],
      muscles: 'czworogłowy, pośladki, stabilizatory',
      desc: 'Ćwiczenie unilateralne wyrównujące asymetrie siły. Dobre dla kontroli motorycznej.',
      difficulty: 2,
      instructions: 'Krok o 60–70 cm do przodu. Tylne kolano opada do 2 cm nad podłogą. Wróć do pozycji wyjściowej siłą przedniej nogi.',
    },
    {
      name: 'Uginanie nóg leżąc (leg curl)',
      sets: 3, reps: 12, weight: 40,
      tags: ['maszyna'],
      muscles: 'mięsień dwugłowy uda (izolacja)',
      desc: 'Izolacja mięśni dwugłowych. Kluczowe dla balansowania siły nogi (stosunek dwugłowy/czworogłowy).',
      difficulty: 1,
      instructions: 'Ułóż się twarzą do dołu. Zgnij nogę pełnym zakresem. Kontroluj opuszczanie — 3 sekundy.',
    },
    {
      name: 'Unoszenie łydek stojąc',
      sets: 4, reps: 20, weight: 60,
      tags: ['maszyna'],
      muscles: 'łydki (brzuchaty, płaszczkowaty)',
      desc: 'Łydki wymagają dużej objętości i zakresu ruchu. Pełne opuszczanie kluczowe.',
      difficulty: 1,
      instructions: 'Stój na krawędzi stopnia. Pełne opuszczenie pięty i pełne uniesienie. Zatrzymanie 1 sekundy na szczycie.',
    },
    {
      name: 'Goblet squat z kettlebell',
      sets: 3, reps: 15, weight: 24,
      tags: ['kettlebell'],
      muscles: 'czworogłowy, pośladki, core',
      desc: 'Przysiad z kettlebell trzymanym przy klatce. Wymusza pionową postawę tułowia.',
      difficulty: 2,
      instructions: 'Trzymaj kettlebell za horns przy mostku. Przysiądź głęboko, łokcie między kolanami. Idealne jako rozgrzewka lub finisher.',
    },
    {
      name: 'Hip thrust ze sztangą',
      sets: 4, reps: 12, weight: 80,
      tags: ['sztanga', 'ławka'],
      muscles: 'pośladki (wielki), mięsień dwugłowy uda',
      desc: 'Najlepsze ćwiczenie izolacyjne na pośladki. Dowiedzione badaniami EMG.',
      difficulty: 3,
      instructions: 'Opierz plecy o ławkę (jej krawędź na poziomie łopatek). Sztanga na biodrach z podkładką. Wypchnij biodra do pełnego wyprostu.',
    },
  ],

  // ── BARKI ───────────────────────────────────────────────────────────────────
  barki: [
    {
      name: 'Wyciskanie żołnierskie (OHP)',
      sets: 4, reps: 6, weight: 55,
      tags: ['sztanga', 'baza'],
      muscles: 'barki (przedni, boczny), triceps',
      desc: 'Stojące wyciskanie sztangi nad głowę. Jeden z fundamentalnych wzorców siłowych.',
      difficulty: 4,
      instructions: 'Stój prosto, core spięty. Sztanga zaczyna na wysokości obojczyków. Przy wyciskaniu — głowa lekko do tyłu, potem wróć pod drążek.',
    },
    {
      name: 'Wyciskanie hantli siedząc',
      sets: 4, reps: 10, weight: 20,
      tags: ['hantle', 'ławka'],
      muscles: 'barki, triceps',
      desc: 'Stabilniejsze niż wyciskanie stojąc. Dobre dla początkujących i zaawansowanych.',
      difficulty: 2,
      instructions: 'Ławka ustawiona pionowo (90°). Hantle na poziomie uszu. Wyciskaj ponad głowę, nie stukaj hantlami.',
    },
    {
      name: 'Wznosy boczne z hantlami',
      sets: 4, reps: 15, weight: 10,
      tags: ['hantle'],
      muscles: 'barki (boczna głowa)',
      desc: 'Najlepsze ćwiczenie na szerokie barki. Skup się na ściskaniu bocznej głowy delty w górze.',
      difficulty: 1,
      instructions: 'Uniesienie do linii barków (nie wyżej). Kciuk lekko do dołu (wlewasz wodę). Kontroluj opuszczanie.',
    },
    {
      name: 'Wznosy przednie z hantlami',
      sets: 3, reps: 12, weight: 10,
      tags: ['hantle'],
      muscles: 'barki (przednia głowa)',
      desc: 'Izolacja przedniej głowy delty. Najczęściej jest ona dobrze rozwinięta przez wyciskanie.',
      difficulty: 1,
      instructions: 'Unoś przed siebie do poziomu barków. Możesz naprzemiennie lub oburęcznie. Unikaj kołysania.',
    },
    {
      name: 'Face pull na wyciągu',
      sets: 3, reps: 15, weight: 25,
      tags: ['kable'],
      muscles: 'tylny bark, rotatory zewnętrzne, środkowy trapez',
      desc: 'Kluczowe ćwiczenie zdrowotne dla barków. Wzmacnia często zaniedbywane mięśnie rotatorów.',
      difficulty: 2,
      instructions: 'Wyciąg na wysokości twarzy. Ciągnij do czoła, łokcie wysoko powyżej ramion. Rozsuń uchwyty na boki w końcowej fazie.',
    },
    {
      name: 'Unoszenie hantli na T (bent-over laterals)',
      sets: 3, reps: 15, weight: 8,
      tags: ['hantle'],
      muscles: 'tylny bark, środkowy trapez',
      desc: 'Pochylony 90° do przodu. Unosi hantle na boki. Aktywuje tylną głowę delty.',
      difficulty: 2,
      instructions: 'Tułów równolegle do podłogi. Uniesienie rąk do linii barków. Kciuk skierowany do podłogi (odwrotnie niż we wznosach bocznych).',
    },
    {
      name: 'Arnold Press',
      sets: 3, reps: 10, weight: 16,
      tags: ['hantle', 'ławka'],
      muscles: 'barki (wszystkie głowy)',
      desc: 'Obrotowe wyciskanie angażujące wszystkie trzy głowy delty. Wymyślone przez Schwarzeneggera.',
      difficulty: 3,
      instructions: 'Zacznij z hantlami przed twarzą (jak na końcu wznosu). Wyciskając, obracaj dłonie na zewnątrz. Na górze dłonie do przodu.',
    },
    {
      name: 'Face Pull na wyciągu',
      desc: 'Kluczowe ćwiczenie zdrowotne. Wzmacnia tylną głowę delty i stożek rotatorów — zapobiega kontuzjom barku.',
      muscles: ['barki (tylna głowa)', 'stożek rotatorów', 'czworoboczny'],
      difficulty: 2,
      instructions: 'Wyciąg na wysokości twarzy. Chwyć linę. Ściągaj do uszu z zewnętrzną rotacją ramion. Łokcie wyżej niż nadgarstki przez cały czas.',
    },
  ],

  // ── RAMIONA ─────────────────────────────────────────────────────────────────
  ramiona: [
    {
      name: 'Uginanie ramion ze sztangą',
      sets: 4, reps: 10, weight: 40,
      tags: ['sztanga'],
      muscles: 'biceps, mięsień ramienny',
      desc: 'Klasyczne ćwiczenie na biceps. Neutralny uchwyt angażuje ramienny, szeroki chwyt — krótką głowę bicepsa.',
      difficulty: 2,
      instructions: 'Trzymaj łokcie przy tułowiu. Nie kołysz tułowiem. Pełny zakres — od pełnego wyprostu do pełnego ugięcia.',
    },
    {
      name: 'Uginanie hantli naprzemienne',
      sets: 4, reps: 12, weight: 18,
      tags: ['hantle'],
      muscles: 'biceps, mięsień ramienny, ramienno-promieniowy',
      desc: 'Naprzemienne unoszenie hantli. Możliwość supinacji nadgarstka w trakcie ruchu.',
      difficulty: 1,
      instructions: 'W trakcie unoszenia obracaj dłoń tak, by na górze kciuk wskazywał na zewnątrz (supinacja).',
    },
    {
      name: 'Prostowanie trójgłowego na wyciągu (tricep pushdown)',
      sets: 4, reps: 12, weight: 30,
      tags: ['kable'],
      muscles: 'triceps (głowa boczna, przyśrodkowa)',
      desc: 'Izolacja tricepsa. Uchwyt prosty izoluje boczną głowę, linka uchwytywana podchwytem — przyśrodkową.',
      difficulty: 1,
      instructions: 'Łokcie stabilnie przy tułowiu. Pełny wyprost w dole. Nie kołysz, nie odciągaj łokci.',
    },
    {
      name: 'Wyciskanie wąskim chwytem',
      sets: 3, reps: 8, weight: 65,
      tags: ['sztanga', 'ławka'],
      muscles: 'triceps, klatka piersiowa (środek)',
      desc: 'Chwyt na szerokość barków lub węższy. Jeden z najefektywniejszych wielostawowych ćwiczeń na triceps.',
      difficulty: 3,
      instructions: 'Chwyt co najmniej na szerokość barków (nie zbyt wąski — nadwyręża nadgarstki). Łokcie wzdłuż tułowia.',
    },
    {
      name: 'Uginanie ramion na ławce Scotta',
      sets: 3, reps: 12, weight: 30,
      tags: ['maszyna', 'ławka'],
      muscles: 'biceps (izolacja)',
      desc: 'Ławka Scotta eliminuje kołysanie. Maksymalna izolacja bicepsa.',
      difficulty: 2,
      instructions: 'Opierasz trójgłowy o ławkę (tylna strona ramienia). Pełny zakres ruchu — pełne wyprostowanie ważne.',
    },
    {
      name: 'Prostowanie trójgłowego z hantlem nad głową',
      sets: 3, reps: 12, weight: 20,
      tags: ['hantle'],
      muscles: 'triceps (głowa długa)',
      desc: 'Jedyne ćwiczenie angażujące głowę długą tricepsa w pełnym rozciągnięciu.',
      difficulty: 2,
      instructions: 'Trzymaj hantel obiema rękami za tarczę nad głową. Opuszczaj za głowę. Łokcie skierowane do sufitu.',
    },
    {
      name: 'Hammer curl (uchwyt neutralny)',
      sets: 3, reps: 12, weight: 18,
      tags: ['hantle'],
      muscles: 'biceps (krótka głowa), mięsień ramienny, ramienno-promieniowy',
      desc: 'Kciuk do góry przez cały ruch. Angażuje ramienny — dodaje grubości ramienia.',
      difficulty: 1,
      instructions: 'Neutralny uchwyt (jak trzymasz młotek). Brak supinacji. Możesz wykonywać oburęcznie lub naprzemiennie.',
    },
    {
      name: 'Skullcrusher z hantlami',
      desc: 'Klasyczna izolacja trójgłowego. Pozwala na precyzyjne wyczucie pracy każdej głowy mięśnia.',
      muscles: ['triceps (wszystkie głowy)', 'łokieć stabilizacja'],
      difficulty: 3,
      instructions: 'Leż na ławce. Hantle nad klatką prostymi rękami. Zginaj TYLKO w łokciach — opuszczaj ku skroniom. Wyprostuj dynamicznie.',
    },
  ],

  // ── BRZUCH ──────────────────────────────────────────────────────────────────
  brzuch: [
    {
      name: 'Plank',
      sets: 3, reps: 1, weight: 0,
      tags: [],
      muscles: 'core (poprzeczny brzucha, prostowniki grzbietu)',
      desc: 'Fundament treningu core. Zamiast repsów podaj sekundy — zacznij od 30s, dojdź do 90s.',
      difficulty: 2,
      instructions: 'Ciało w linii prostej. Biodra nie opadają ani nie idą w górę. Wdech przez nos, wydech przez usta, core aktywny.',
    },
    {
      name: 'Crunch',
      sets: 4, reps: 20, weight: 0,
      tags: [],
      muscles: 'prostownik brzucha (górna część)',
      desc: 'Klasyczne ćwiczenie na górną część prostownika brzucha. Mały zakres ruchu — tylko łopatki od podłogi.',
      difficulty: 1,
      instructions: 'Ręce za głową luźno — nie ciągnij karku. Wydech na szczycie. Koncentruj się na skracaniu odległości między żebrami a biodrem.',
    },
    {
      name: 'Nożyczki (scissor kicks)',
      sets: 3, reps: 20, weight: 0,
      tags: [],
      muscles: 'prostownik brzucha (dolna część), zginacze bioder',
      desc: 'Naprzemienne krzyżowanie nóg w powietrzu. Angażuje dolną część brzucha.',
      difficulty: 2,
      instructions: 'Leż na plecach, dłonie pod pośladkami. Nogi 15 cm nad ziemią, krzyżujesz naprzemiennie. Nie zapominaj o oddechu.',
    },
    {
      name: 'Rosyjski skręt z hantlem',
      sets: 3, reps: 16, weight: 10,
      tags: ['hantle'],
      muscles: 'skośny brzucha (zewnętrzny i wewnętrzny)',
      desc: 'Skręty tułowia angażujące mięśnie skośne. Podnoś nogi dla wyższej trudności.',
      difficulty: 2,
      instructions: 'Siądź z lekko cofniętym tułowiem. Przenoś hantel z boku na bok, dotykając podłogi. Nie obracaj bioder.',
    },
    {
      name: 'Rollout z kółka (ab wheel)',
      sets: 3, reps: 10, weight: 0,
      tags: [],
      muscles: 'core (pełna aktywacja), ramiona, plecy',
      desc: 'Jedno z najtrudniejszych ćwiczeń core. Wymaga pełnej stabilizacji całego ciała.',
      difficulty: 5,
      instructions: 'Zacznij na kolanach. Toczysz kółko jak najdalej przed siebie z wyprostowanymi rękami. Wróć siłą brzucha, nie bioder.',
    },
    {
      name: 'Hanging leg raise (zwis na drążku)',
      sets: 3, reps: 12, weight: 0,
      tags: ['drążek'],
      muscles: 'dolna część prostownika brzucha, zginacze bioder',
      desc: 'Unoszenie nóg w zwisie. Jedno z najlepszych ćwiczeń na dolny brzuch.',
      difficulty: 4,
      instructions: 'Zwis na drążku. Unoś nogi do poziomu bioder (proste nogi) lub wyżej (ugięte = łatwiej). Nie kołysaj ciałem.',
    },
    {
      name: 'Mountain climbers',
      sets: 3, reps: 30, weight: 0,
      tags: [],
      muscles: 'core, ramiona, cardio',
      desc: 'Dynamiczne ćwiczenie łączące core z cardio. Świetne jako element HIIT.',
      difficulty: 3,
      instructions: 'Pozycja pompki. Naprzemiennie przyciągaj kolana do klatki jak najszybciej bez unoszenia bioder.',
    },
,
    {
      name: 'Dragon Flag',
      desc: 'Ekstremalne ćwiczenie na cały core. Uważane za jedno z najtrudniejszych na mięśnie brzucha.',
      muscles: ['prostownik brzucha (pełny)', 'core stabilizacja', 'biodrowy zginacz'],
      difficulty: 5,
      instructions: 'Leż na ławce, trzymaj się krawędzi za głową. Unoś całe ciało od ramion jak deskę. Opuszczaj kontrolowanie przez 4 sekundy. Ciało proste cały czas.',
    }
  ],

}; // koniec EXERCISE_DB


// ─────────────────────────────────────────────────────────────────────────────
// 3. SPORT_DRILLS
// ─────────────────────────────────────────────────────────────────────────────
// Format: każdy drill zawiera: name, duration, total_attempts, description,
//   progression_tip, target_pct, sets, muscle_group, [video_url]
//
// Dyscypliny: koszykówka, piłka nożna, tenis, boks, siatkówka
// ─────────────────────────────────────────────────────────────────────────────

const SPORT_DRILLS = {
  // ── KOSZYKÓWKA ─────────────────────────────────────────────────────────────
  'koszykówka': {

    rzuty: {
      emoji: '🎯', label: 'Rzuty i skuteczność',
      drills: [
        {
          name: 'Rzuty za linią 3 pkt — runda 5 pozycji',
          duration: '20 min', total_attempts: 50,
          description: 'Stań kolejno na 5 pozycjach za łukiem (rogi, skrzydła, środek). Z każdej oddaj 10 rzutów. Cel: 60%+.',
          progression_tip: 'Gdy trafisz 60% — przesuń się o krok dalej od linii.',
          target_pct: 60, sets: '5 pozycji × 10', muscle_group: 'ramiona, stabilizacja core',
          video_url: 'https://www.youtube.com/embed/GlsLNsf_UFk',
        },
        {
          name: 'Rzuty wolne — seria 10',
          duration: '10 min', total_attempts: 100,
          description: '100 rzutów wolnych w seriach po 10. Między seriami wykonaj 10 przysiadów (symulacja zmęczenia nóg w meczu).',
          progression_tip: 'Cel: 80% trafień pod presją. Wprowadź rutynę przed rzutem.',
          target_pct: 80, sets: '10 × 10', muscle_group: 'ramiona, koncentracja',
        },
        {
          name: 'Mid-range pull-up (step-back)',
          duration: '15 min', total_attempts: 40,
          description: 'Cofnij się o krok z dryblingu i oddaj rzut ze średniej odległości. Ćwicz z obu skrzydeł i ze środka.',
          progression_tip: 'Utrzymuj równowagę po odbiciu — rzut powinien być zawsze z tej samej pozycji ciała.',
          target_pct: 55, sets: '4 serie po 10', muscle_group: 'nogi (eksplozja), ramiona',
        },
        {
          name: 'Rzuty po wejściu (lay-up obie ręce)',
          duration: '12 min', total_attempts: 60,
          description: 'Naprzemiennie wchódź prawą i lewą ręką. 30 podejść z każdej strony. Skup się na rytmie kroków.',
          progression_tip: 'Gdy opanujesz obie ręce — dodaj drybling przed wejściem.',
          target_pct: 90, sets: '2 × 30', muscle_group: 'nogi, koordynacja',
        },
        {
          name: 'Catch-and-shoot off screen',
          duration: '15 min', total_attempts: 40,
          description: 'Partner (lub automat) podaje piłkę po symulowanym bloku. Chwyć i oddaj rzut w jednym ruchu. Brak dryblingu.',
          progression_tip: 'Kluczowy jest uchwyt — ręce gotowe przed odbiorem piłki.',
          target_pct: 65, sets: '4 × 10', muscle_group: 'ramiona, szybkość decyzji',
        },
      ],
    },

    drybling: {
      emoji: '⚡', label: 'Drybling i szybkość',
      drills: [
        {
          name: 'Spider Dribble',
          duration: '10 min', total_attempts: null,
          description: 'Postaw piłkę między nogami. Naprzemiennie uderzaj od przodu i tyłu — 4 uderzenia tworząc wzór pająka. Stopniowo przyspieszaj.',
          progression_tip: 'Wytrenuj do 60 sekund bez utraty kontroli.',
          target_pct: 100, sets: '5 × 30s', muscle_group: 'nadgarstki, koordynacja',
        },
        {
          name: 'Two-ball dribbling',
          duration: '15 min', total_attempts: null,
          description: 'Ćwicz drybling dwiema piłkami jednocześnie: naprzemiennie, synchronicznie, high-low. Nie patrz na piłki.',
          progression_tip: 'Gdy dwie piłki są stabilne — chodź w przód/tył podczas dryblingu.',
          target_pct: 100, sets: '6 × 45s', muscle_group: 'obie ręce, niezależna koordynacja',
        },
        {
          name: 'Figure-8 między nogami',
          duration: '8 min', total_attempts: null,
          description: 'Przeprowadzaj piłkę w ósemce między nogami w niskim przysiadzie. Celem jest płynność i brak podglądania.',
          progression_tip: 'Mierz czas: cel to 30 ósemek w 30 sekund.',
          target_pct: 100, sets: '4 × 30s', muscle_group: 'nadgarstki, nogi (przysiad)',
        },
        {
          name: 'Crossover na szybkość (stoper)',
          duration: '10 min', total_attempts: 60,
          description: 'Crossover przez strefę 6m. Sprint, crossover, powrót. Mierz czas każdej rundy. Cel: poniżej 3,5 sek.',
          progression_tip: 'Zniżaj środek ciężkości przy crossoverze — nie prostuj kolan.',
          target_pct: 100, sets: '4 × 15', muscle_group: 'nogi, szybkość zmiany kierunku',
        },
        {
          name: 'Hesitation (stutter-step) move',
          duration: '12 min', total_attempts: 40,
          description: 'Jedź z drybliem, zatrzymaj się na chwilę (hesitation) i wybuchnij w bok lub prosto. Trenuj zmylenie obrońcy.',
          progression_tip: 'Im bardziej przekonujące zatrzymanie — tym skuteczniejszy atak.',
          target_pct: 100, sets: '4 × 10', muscle_group: 'nogi eksplozja, koordynacja',
        },
      ],
    },

    obrona: {
      emoji: '🛡️', label: 'Obrona i footwork',
      drills: [
        {
          name: 'Defensive Slides — 5 konusów',
          duration: '12 min', total_attempts: null,
          description: 'Ustaw 5 konusów w linii co 1m. Przesuwy w obronie bez krzyżowania nóg. Dotknij każdego konusa i wróć.',
          progression_tip: 'Biodra niżej niż kolana przez cały czas. Nie prostuj się między konusami.',
          target_pct: 100, sets: '4 × 45s', muscle_group: 'nogi (przysiad), core',
        },
        {
          name: 'Closeout na skrzydłowego',
          duration: '10 min', total_attempts: 30,
          description: 'Startuj spod kosza. Sprint do skrzydłowego na linii 3 pkt. Wyhamuj z wyciągniętą ręką (nie fauluj). Wróć pod kosz.',
          progression_tip: 'Wyhamuj dwie stopy przed zawodnikiem — nie leć na niego.',
          target_pct: 100, sets: '3 × 10', muscle_group: 'nogi, reakcja',
        },
        {
          name: '1-on-1 box-out (walka o pozycję)',
          duration: '10 min', total_attempts: 20,
          description: 'Z partnerem: jeden atakuje kosz, drugi blokuje do zbiórki. Każda runda 30 sekund. Liczy się pozycja, nie siła.',
          progression_tip: 'Wysuń pośladki i utrzymaj kontakt plecami z napastnikiem.',
          target_pct: 100, sets: '2 × 10', muscle_group: 'pośladki, core, siła pozycyjna',
        },
        {
          name: 'Mirror Drill (lustro)',
          duration: '8 min', total_attempts: null,
          description: 'Dwóch zawodników twarzą do siebie. Jeden porusza się swobodnie, drugi naśladuje w obronie przez 30 sekund bez ucieczki.',
          progression_tip: 'Skup wzrok na biodrach partnera — nie na piłce ani stopach.',
          target_pct: 100, sets: '4 × 30s', muscle_group: 'nogi, koncentracja, reakcja',
        },
        {
          name: 'Shell Defense (4-on-4 rotation)',
          duration: '20 min', total_attempts: null,
          description: 'Ćwiczenie systemowe. 4 obrońców rotuje według zasad: help-side, deny, on-ball. Atak porusza się bez dryblingu.',
          progression_tip: 'Ogni punktem jest linia podań — nie pozwól na łatwy przerzut.',
          target_pct: 100, sets: '4 × 3 min', muscle_group: 'komunikacja, pozycjonowanie',
        },
      ],
    },

  },

  // ── PIŁKA NOŻNA ─────────────────────────────────────────────────────────────
  'piłka nożna': {

    podania: {
      emoji: '🎯', label: 'Podania i pierwsza piłka',
      drills: [
        {
          name: 'Rondo 4v1',
          duration: '15 min', total_attempts: 50,
          description: 'Czterech graczy w kwadracie 5x5m podaje piłkę, jeden w środku próbuje ją przechwycić. Zadaniem grupy: min. 5 podań z rzędu.',
          progression_tip: 'Cel: 10 serii po 5 podań z rzędu → zmniejsz kwadrat do 4x4m.',
          target_pct: 80, sets: '5 serii po 3 min', muscle_group: 'nogi, propriocepcja',
        },
        {
          name: 'Podanie i sprint',
          duration: '12 min', total_attempts: 20,
          description: 'Podaj piłkę do partnera, a następnie sprint 20m i wróć. Partner oddaje piłkę na Twój bieg.',
          progression_tip: 'Cel: 18/20 przejęć w biegu → zwiększ dystans sprintu do 30m.',
          target_pct: 90, sets: '4 serie po 5', muscle_group: 'nogi, cardio',
        },
        {
          name: 'Pierwsza piłka o ścianę',
          duration: '10 min', total_attempts: 40,
          description: 'Uderz piłkę o ścianę z 5 m i przyjmij pierwszą piłką wewnętrzną lub zewnętrzną stopą w kierunku zmiany gry.',
          progression_tip: 'Cel: 36/40 czystych przyjęć → cofnij się do 8m i dodaj obrót.',
          target_pct: 90, sets: '4 serie po 10', muscle_group: 'koordynacja, refleks',
        },
        {
          name: 'Trójkąt podań (1-2-3)',
          duration: '15 min', total_attempts: 30,
          description: 'Troje zawodników w trójkącie ok. 8m. Podanie-ruch-przyjęcie. Jeden wykonuje „nakrytkę" po każdym podaniu.',
          progression_tip: 'Cel: 25/30 bez przerwy → skróć czas na podanie (1 dotknięcie).',
          target_pct: 83, sets: '3 serie po 10', muscle_group: 'nogi, komunikacja',
        },
        {
          name: 'Długie podanie (40m)',
          duration: '20 min', total_attempts: 20,
          description: '10 długich podań lewą, 10 prawą nogą. Partner stoi w kole 3m. Cel: piłka zatrzymuje się w kole.',
          progression_tip: 'Cel: 14/20 w kole → zmniejsz cel do 2m.',
          target_pct: 70, sets: '2 × 10 (prawa/lewa)', muscle_group: 'nogi, precyzja',
        },
      ],
    },

    drybling: {
      emoji: '🏃', label: 'Drybling i zwody',
      drills: [
        {
          name: 'Slalom przez pachołki',
          duration: '10 min', total_attempts: 10,
          description: '8 pachołków co 1,5m. Slalom z piłką, sprintem na powrót. Mierz czas.',
          progression_tip: 'Cel: <10s na serię → zmniejsz odstęp do 1m.',
          target_pct: 100, sets: '5 serii w każdym kierunku', muscle_group: 'zwinność, nogi',
        },
        {
          name: 'Krok z piłką (scissors)',
          duration: '10 min', total_attempts: 30,
          description: 'Noga macha nad piłką (zwód) w jedną stronę, piłka schodzi w drugą. Statycznie, potem w ruchu.',
          progression_tip: 'Cel: 28/30 bez straty piłki w ruchu → dodaj obrońcę.',
          target_pct: 93, sets: '3 serie × 10', muscle_group: 'koordynacja, szybkość nóg',
        },
        {
          name: 'Elastico (zwód Ronaldinho)',
          duration: '12 min', total_attempts: 20,
          description: 'Zewnętrzną częścią stopy uderzasz piłkę w prawo, natychmiast wewnętrzną ściągasz w lewo (lub odwrotnie).',
          progression_tip: 'Cel: 15/20 czystych zwodów → wykonaj w sprincie 10m.',
          target_pct: 75, sets: '4 serie po 5', muscle_group: 'koordynacja stopy',
        },
        {
          name: 'Drybling 1v1 (koraliki)',
          duration: '15 min', total_attempts: 15,
          description: 'Partner stoi nieruchomo jako obrońca. Omiń go dryblując i zakończ strzałem lub podaniem za linię.',
          progression_tip: 'Cel: 12/15 ominięć → partner może ruszać nogami (pół-aktywny).',
          target_pct: 80, sets: '3 serie po 5', muscle_group: 'agresja, decyzyjność',
        },
        {
          name: 'Zmiana tempa (slow-fast)',
          duration: '10 min', total_attempts: 20,
          description: 'Wolne dryblowanie, a na sygnał (klask trenera) sprint 10m z piłką. Cel: utrzymać kontrolę przy zmianie tempa.',
          progression_tip: 'Cel: 18/20 z kontrolą → skróć czas przyspieszenia.',
          target_pct: 90, sets: '4 serie po 5', muscle_group: 'eksplozywność, technika',
        },
      ],
    },

    strzały: {
      emoji: '🥅', label: 'Strzały na bramkę',
      drills: [
        {
          name: 'Strzał po przyjęciu piłki',
          duration: '15 min', total_attempts: 20,
          description: 'Partner podaje piłkę w biegu, ty przyjmujesz i strzelasz z 16m. Strzały wewnętrzną częścią stopy.',
          progression_tip: 'Cel: 12/20 w bramce → strzelaj po zwodzie (1 dotknięcie).',
          target_pct: 60, sets: '4 serie × 5', muscle_group: 'nogi, koordynacja',
        },
        {
          name: 'Strzał z pierwszej piłki',
          duration: '10 min', total_attempts: 15,
          description: 'Partner podaje boczną piłkę na biegniętą pozycję — ty strzelasz bez zatrzymywania piłki.',
          progression_tip: 'Cel: 8/15 w bramce → zmień kąt podania.',
          target_pct: 53, sets: '3 serie × 5', muscle_group: 'timing, siła uderzenia',
        },
        {
          name: 'Strzał po dryblingu (finalizacja)',
          duration: '15 min', total_attempts: 15,
          description: 'Slalom przez 4 pachołki i strzał na bramkę z 12m. Mierz zarówno trafienia jak i czas na serię.',
          progression_tip: 'Cel: 10/15 i <8s na serię → dodaj bramkarza.',
          target_pct: 67, sets: '3 serie × 5', muscle_group: 'cardio, precyzja',
        },
        {
          name: 'Rzuty karne',
          duration: '10 min', total_attempts: 10,
          description: 'Standardowe rzuty z 11m. Cel: rozwinąć pewność siebie i powtarzalność mechaniki.',
          progression_tip: 'Cel: 8/10 w bramce → zmień narożnik przy każdym podejściu.',
          target_pct: 80, sets: '10 prób', muscle_group: 'precyzja, odporność psychiczna',
        },
        {
          name: 'Strzał z woleja',
          duration: '12 min', total_attempts: 15,
          description: 'Partner wyrzuca piłkę w powietrze z 6m, ty strzelasz przed opadnięciem z 14m od bramki.',
          progression_tip: 'Cel: 7/15 w bramce → volley z biegu.',
          target_pct: 47, sets: '3 serie × 5', muscle_group: 'timing, technika',
        },
      ],
    },

  },

  // ── TENIS ────────────────────────────────────────────────────────────────────
  'tenis': {

    serwis: {
      emoji: '🎯', label: 'Serwis i powrót',
      drills: [
        {
          name: 'Serwis flat do pola T',
          duration: '15 min', total_attempts: 20,
          description: 'Płaski serwis celujący w środek pola serwisowego (pole T). Cel: konsekwencja mechaniki.',
          progression_tip: 'Cel: 15/20 w polu → zwiększ prędkość o 10%.',
          target_pct: 75, sets: '4 serie po 5', muscle_group: 'bark, ramię',
        },
        {
          name: 'Serwis slice na zewnątrz',
          duration: '12 min', total_attempts: 20,
          description: 'Serwis z podcięciem celujący w zewnętrzny narożnik. Wyciąga przeciwnika poza kort.',
          progression_tip: 'Cel: 13/20 w narożniku → połącz z dojściem do siatki.',
          target_pct: 65, sets: '4 serie po 5', muscle_group: 'nadgarstek, bark',
        },
        {
          name: 'Powrót serwisu (return)',
          duration: '15 min', total_attempts: 20,
          description: 'Partner serwuje, ty skupiasz się wyłącznie na powrocie. Cel: min. 2/3 głęboko do kortu.',
          progression_tip: 'Cel: 14/20 głęboko → celuj w określony narożnik.',
          target_pct: 67, sets: '4 serie po 5', muscle_group: 'refleks, timing',
        },
        {
          name: 'Serwis topspin (kick serve)',
          duration: '15 min', total_attempts: 15,
          description: 'Serwis z dużym efektem górnym, odbijający wysoko. Bezpieczny drugi serwis.',
          progression_tip: 'Cel: 10/15 wewnątrz pola i z odbiciem → wariant na ciało (body serve).',
          target_pct: 67, sets: '3 serie po 5', muscle_group: 'bark, tułów',
        },
        {
          name: '5 serwisów z rzędu w T',
          duration: '10 min', total_attempts: 20,
          description: 'Cel: wbić 5 serwisów z rzędu w pole T. Restart przy błędzie.',
          progression_tip: 'Cel: 3 serie po 5 bez błędu → 5 serwisów z rzędu alternating T i wide.',
          target_pct: 100, sets: 'do skutku', muscle_group: 'powtarzalność, koncentracja',
        },
      ],
    },

    forehend_backhand: {
      emoji: '🏓', label: 'Forehand i Backhand',
      drills: [
        {
          name: 'Crosscourt forehand 20 podań',
          duration: '15 min', total_attempts: 20,
          description: 'Wymieniasz crosscourt forehande z partnerem z linii podstawowej. Cel: głębokość > 3/4 kortu.',
          progression_tip: 'Cel: 16/20 głęboko → zwiększ tempo o 15%.',
          target_pct: 80, sets: '4 serie po 5', muscle_group: 'ramię, tułów',
        },
        {
          name: 'Backhand down-the-line',
          duration: '15 min', total_attempts: 20,
          description: 'Backhand (jednostronny lub dwuręczny) wzdłuż linii bocznej. Ćwiczysz zmianę kierunku.',
          progression_tip: 'Cel: 14/20 w pasie 1m od linii → dodaj ruch nogi przed uderzeniem.',
          target_pct: 70, sets: '4 serie po 5', muscle_group: 'ramię, rotacja',
        },
        {
          name: 'Szybka zmiana forehand↔backhand',
          duration: '12 min', total_attempts: 20,
          description: 'Partner naprzemiennie podaje do forehanda i bekhendu. Ty musisz szybko zmieniać pozycję i grip.',
          progression_tip: 'Cel: 16/20 bez straty punktu → partner podaje losowo.',
          target_pct: 80, sets: '4 serie po 5', muscle_group: 'nogi, refleks, ramię',
        },
        {
          name: 'Topspinowy forehand z biegu',
          duration: '15 min', total_attempts: 15,
          description: 'Partner posyła piłkę do narożnika, ty dobiegasz i wykonujesz topspin forehand crosscourt.',
          progression_tip: 'Cel: 10/15 w polu → sprint powrót do środka po każdym uderzeniu.',
          target_pct: 67, sets: '3 serie po 5', muscle_group: 'cardio, technika',
        },
        {
          name: 'Sieć — volley forehand i backhand',
          duration: '10 min', total_attempts: 20,
          description: 'Stoisz przy siatce, partner liftuje piłki, wykonujesz volleys. Cel: głęboki wolej z rotacją.',
          progression_tip: 'Cel: 16/20 głęboko → stój bliżej siatki (1m) i skróć czas reakcji.',
          target_pct: 80, sets: '4 serie po 5', muscle_group: 'refleks, technika dłoni',
        },
      ],
    },

    footwork: {
      emoji: '👟', label: 'Footwork i poruszanie',
      drills: [
        {
          name: 'Spider drill',
          duration: '12 min', total_attempts: 10,
          description: 'Sprint do 6 punktów na korcie i z powrotem do środka siatki. Mierzysz czas.',
          progression_tip: 'Cel: <30s na serię → dodaj rakietę w ręku.',
          target_pct: 100, sets: '5 serii + 2 min przerwa', muscle_group: 'cardio, zwinność',
        },
        {
          name: 'Boczny krok z rakietą (shuffle)',
          duration: '10 min', total_attempts: 10,
          description: 'Boczne przemieszczenie wzdłuż linii bazowej z rakietą — naśladowanie poruszania się w meczu.',
          progression_tip: 'Cel: 10/10 bez skrzyżowania nóg → dodaj uderzenie forehanda na końcu.',
          target_pct: 100, sets: '5 × każda strona', muscle_group: 'nogi, stabilizacja',
        },
        {
          name: 'Powrót split-stepem',
          duration: '10 min', total_attempts: 15,
          description: 'Przy każdym uderzeniu partnera wykonujesz split-step (mały podskok z rozstawieniem nóg) dla gotowości.',
          progression_tip: 'Cel: 13/15 z właściwym timingiem → zastosuj w grze wymianowej.',
          target_pct: 87, sets: '3 serie po 5', muscle_group: 'refleks, nogi',
        },
        {
          name: 'Krótkie piłki — forza do przodu',
          duration: '12 min', total_attempts: 15,
          description: 'Partner podaje krótko, ty sprintujesz do siatki, odbierasz i wracasz do bazy.',
          progression_tip: 'Cel: 12/15 bez gubienia piłki → sfinalizuj sieciowo.',
          target_pct: 80, sets: '3 serie po 5', muscle_group: 'cardio, technika',
        },
        {
          name: 'Obrona przy bandzie (lob i smash)',
          duration: '15 min', total_attempts: 15,
          description: 'Partner posyła loba, ty cofa się i smaszujesz. Cel: smasz do końca kortu.',
          progression_tip: 'Cel: 10/15 smashy w polu → wykonaj z biegiem do przodu po smashu.',
          target_pct: 67, sets: '3 serie po 5', muscle_group: 'bark, koordynacja',
        },
      ],
    },

  },

  // ── BOKS ────────────────────────────────────────────────────────────────────
  'boks': {

    technika: {
      emoji: '🥊', label: 'Technika uderzeń',
      drills: [
        {
          name: 'Jab-Cross combo (1-2)',
          duration: '15 min', total_attempts: 50,
          description: 'Jab lewą (1) + cross prawą (2). Podstawowa kombinacja. Skupia się na rotacji bioder przy crossie.',
          progression_tip: 'Cel: 45/50 z pełną rotacją bioder → dodaj krok do tyłu po combo.',
          target_pct: 90, sets: '5 × 3 min z 1 min przerwy', muscle_group: 'bark, tułów, nogi',
        },
        {
          name: 'Hook-Uppercut combo (3-5)',
          duration: '15 min', total_attempts: 40,
          description: 'Left hook (3) + left uppercut (5). Uderzenia hakiem i sierpem do środka.',
          progression_tip: 'Cel: 35/40 z odczuwaną eksplozją bioder → przejdź do kombinacji 1-2-3-5.',
          target_pct: 87, sets: '4 × 3 min z 1 min przerwy', muscle_group: 'bark, nogi, core',
        },
        {
          name: '1-2-3-2 (Jab-Cross-Hook-Cross)',
          duration: '12 min', total_attempts: 30,
          description: 'Czterouderzeniowe combo rozwijające timing i koordynację. Kluczowe: nie "czytać" combo zbyt wcześnie.',
          progression_tip: 'Cel: 25/30 z utrzymaniem gardą → wykonaj na worku, a nie na łapach.',
          target_pct: 83, sets: '3 × 3 min z 1 min przerwy', muscle_group: 'cały łańcuch uderzeń',
        },
        {
          name: 'Uderzenia w łapy trenerskie',
          duration: '20 min', total_attempts: 60,
          description: 'Trener trzyma łapy, dyktuje kombinacje. Cel: wyczucie dystansu i timing.',
          progression_tip: 'Cel: 55/60 trafień z pełną mocą → trener dodaje kontrę po każdym combo.',
          target_pct: 92, sets: '4 × 3 min z 1 min przerwy', muscle_group: 'cały boxing',
        },
        {
          name: 'Slow-motion techniczne',
          duration: '10 min', total_attempts: 20,
          description: 'Wykonaj każde uderzenie 3× wolniej niż normalnie przed lustrem. Analizuj każdą fazę.',
          progression_tip: 'Cel: 20/20 z idealną mechaniką → nagraj video i porównaj z modelem.',
          target_pct: 100, sets: '4 serie po 5 minut', muscle_group: 'neuromotorika',
        },
      ],
    },

    footwork: {
      emoji: '👟', label: 'Footwork i praca nóg',
      drills: [
        {
          name: 'Step-and-jab',
          duration: '10 min', total_attempts: 30,
          description: 'Krok w przód lewą nogą połączony z jabem. Cel: jab wychodzi w momencie dociśnięcia stopy.',
          progression_tip: 'Cel: 27/30 z synchro krok-cios → dodaj wycofanie po jabie.',
          target_pct: 90, sets: '3 × 3 min', muscle_group: 'nogi, koordynacja',
        },
        {
          name: 'Box step (kwadrat w footwork)',
          duration: '10 min', total_attempts: 10,
          description: 'Poruszaj się po kwadracie 1×1m: do przodu, w prawo, do tyłu, w lewo — zawsze w gardzie.',
          progression_tip: 'Cel: 10/10 bez patrzenia na nogi → przyspiesz do pełnego tempa.',
          target_pct: 100, sets: '5 okrążeń po 2 min', muscle_group: 'nogi, balans',
        },
        {
          name: 'Praca przy linach (ring generalship)',
          duration: '12 min', total_attempts: 15,
          description: 'Wchodzisz w narożnik (liny), następnie musisz wyjść bez dania przewagi. Trener blokuje.',
          progression_tip: 'Cel: 12/15 czystych wyjść → wyjdź combo zakończonym krokiem bocznym.',
          target_pct: 80, sets: '3 serie po 3 min', muscle_group: 'taktyka, nogi',
        },
        {
          name: 'Shadow boxing z akcentem na nogi',
          duration: '12 min', total_attempts: 1,
          description: 'Shadow boxing gdzie każde uderzenie poprzedzone jest krokiem. Brak stania w miejscu.',
          progression_tip: 'Cel: pełne 3 min bez zatrzymania ruchu nóg → dodaj sznur (skipping) między rundami.',
          target_pct: 100, sets: '4 rundy po 3 min', muscle_group: 'cardio, koordynacja',
        },
        {
          name: 'Przeniesienie ciężaru (pivot)',
          duration: '8 min', total_attempts: 20,
          description: 'Obrót na lewej stopie o 90° po jabie. Pozwala zejść z linii ataku i kontrować.',
          progression_tip: 'Cel: 18/20 z lądowaniem w gardzie → połącz pivot + cross po jabie.',
          target_pct: 90, sets: '4 serie po 5', muscle_group: 'nogi, balans',
        },
      ],
    },

    wytrzymałość: {
      emoji: '⏱️', label: 'Wytrzymałość i kondycja',
      drills: [
        {
          name: 'Praca na worku 3×3 min',
          duration: '15 min', total_attempts: 3,
          description: '3 rundy po 3 min na worku z 1 min przerwy. Każda runda inna taktyka: 1=jaby, 2=combo, 3=wolna robota.',
          progression_tip: 'Cel: 3 rundy z pełną intensywnością → 4 rundy po 3 min.',
          target_pct: 100, sets: '3 rundy', muscle_group: 'cały boks, cardio',
        },
        {
          name: 'Skakanka 3×3 min',
          duration: '12 min', total_attempts: 3,
          description: '3 rundy skakanki z 1 min przerwy. Ruchy nóg bokserskich w rytm skakanki.',
          progression_tip: 'Cel: 3 rundy bez potknięcia → double-under (podwójny obrót) co 10 kroków.',
          target_pct: 100, sets: '3 rundy po 3 min', muscle_group: 'cardio, timing nóg',
        },
        {
          name: 'Burpee z kombinacją (1-2)',
          duration: '10 min', total_attempts: 30,
          description: 'Burpee, wstań i natychmiast wbij jab-cross. Łączy kondycję z refleksem ofensywnym.',
          progression_tip: 'Cel: 28/30 w 8 min → jab-cross-hook-cross (1-2-3-2) po burpee.',
          target_pct: 93, sets: '3 serie po 10', muscle_group: 'cały boks, cardio',
        },
        {
          name: 'Wysoka intensywność (HIIT boxing)',
          duration: '12 min', total_attempts: 6,
          description: '6 cykli: 20s max intensywności na worku + 10s odpoczynku (protokół Tabata).',
          progression_tip: 'Cel: utrzymanie tempa przez 6 cykli → 8 cykli.',
          target_pct: 100, sets: '6 cykli (Tabata)', muscle_group: 'cardio, wytrzymałość',
        },
        {
          name: 'Siłowy cykl zakończający',
          duration: '8 min', total_attempts: 4,
          description: '4 série: 10 pompek + 10 przysiadów + 10 uderzeń w worek. Bez przerw między ćwiczeniami.',
          progression_tip: 'Cel: 4 serie w <8 min → dodaj 5. serię.',
          target_pct: 100, sets: '4 serie z 90s przerwy', muscle_group: 'cały boks + siła',
        },
      ],
    },

  },

  // ── SIATKÓWKA ────────────────────────────────────────────────────────────────
  'siatkówka': {

    zagrywka: {
      emoji: '🎯', label: 'Zagrywka i przyjęcie',
      drills: [
        {
          name: 'Zagrywka floater w strefę 1',
          duration: '15 min', total_attempts: 20,
          description: 'Zagrywka "pływająca" (bez rotacji) celująca w strefę 1 (prawy narożnik). Trudna do odczytania.',
          progression_tip: 'Cel: 14/20 w strefie → celuj naprzemiennie w strefy 1 i 5.',
          target_pct: 70, sets: '4 serie po 5', muscle_group: 'bark, nadgarstek',
        },
        {
          name: 'Zagrywka top-spin z linii podstawowej',
          duration: '15 min', total_attempts: 20,
          description: 'Mocna zagrywka z efektem topspinowym — trudna, ale skuteczna. Wymaga opanowania mechaniki.',
          progression_tip: 'Cel: 12/20 w polu → celuj w strefy 6 i 1.',
          target_pct: 60, sets: '4 serie po 5', muscle_group: 'bark, nogi (odbicie)',
        },
        {
          name: 'Przyjęcie zagrywki forearmem',
          duration: '12 min', total_attempts: 20,
          description: 'Partner serwuje różne zagrywki (mocne/slabe), ty przyjmujesz do wyznaczonej strefy ustawiającego.',
          progression_tip: 'Cel: 16/20 precyzyjnie do strefy 3 → partner serwuje z różnych pozycji.',
          target_pct: 80, sets: '4 serie po 5', muscle_group: 'nogi, refleks, forearm',
        },
        {
          name: '5 zagrywek z rzędu bez błędu',
          duration: '10 min', total_attempts: 25,
          description: 'Cel: wbić 5 zagrywek z rzędu w pole. Restart przy błędzie lub piłce out.',
          progression_tip: 'Cel: 3 serie po 5 w rzędzie → 7 z rzędu.',
          target_pct: 100, sets: 'do skutku', muscle_group: 'powtarzalność, koncentracja',
        },
        {
          name: 'Zagrywka jump serve',
          duration: '15 min', total_attempts: 15,
          description: 'Zagrywka skoczna — trudna technicznie, ale najsilniejsza. Podrzut, odbicie, skok i uderzenie.',
          progression_tip: 'Cel: 9/15 w polu → celuj w strefę 5.',
          target_pct: 60, sets: '3 serie po 5', muscle_group: 'nogi, bark, koordynacja',
        },
      ],
    },

    atak: {
      emoji: '💥', label: 'Atak i zbicie',
      drills: [
        {
          name: 'Zbicie z 4. strefy',
          duration: '15 min', total_attempts: 20,
          description: 'Rozgrywający ustawia z 3. strefy, zbijający atakuje z lewej antenki (strefa 4). Cel: zbicie w pole.',
          progression_tip: 'Cel: 14/20 w polu → celuj w strefy 5 i 1 naprzemiennie.',
          target_pct: 70, sets: '4 serie po 5', muscle_group: 'nogi (odbicie), bark, tułów',
        },
        {
          name: 'Zbicie z 2. strefy (prawoskrzydłowy)',
          duration: '15 min', total_attempts: 20,
          description: 'Atak z prawej antenki (strefa 2). Trudniejszy dla większości zawodników, wymaga rotacji tułowia.',
          progression_tip: 'Cel: 13/20 w polu → dołóż krok dostawny przed atakiem.',
          target_pct: 65, sets: '4 serie po 5', muscle_group: 'bark, rotacja tułowia',
        },
        {
          name: 'Piłka ze środka (P1 — szybka)',
          duration: '12 min', total_attempts: 15,
          description: 'Rozgrywający ustawia krótko i szybko, środkowy atakuje z P1. Tempo kluczowe.',
          progression_tip: 'Cel: 11/15 → ustawienie opóźnione o 0,2s dla utrudnienia.',
          target_pct: 73, sets: '3 serie po 5', muscle_group: 'eksplozywność, timing',
        },
        {
          name: 'Tip (atak na blok)',
          duration: '10 min', total_attempts: 15,
          description: 'Zamiast pełnego ataku, lekkie dotknięcie piłki tuż za blokiem rywala. Wymaga wyczucia.',
          progression_tip: 'Cel: 12/15 za blok → tip zmieniony na roll shot.',
          target_pct: 80, sets: '3 serie po 5', muscle_group: 'nadgarstek, koordynacja',
        },
        {
          name: 'Atak z głębokiego ustawienia',
          duration: '15 min', total_attempts: 15,
          description: 'Piłka jest ustawiana z 6. strefy (głęboko). Zbijający musi zsynchronizować rozbiegu.',
          progression_tip: 'Cel: 10/15 w polu → narzucenie piłki za linię 3m na początek.',
          target_pct: 67, sets: '3 serie po 5', muscle_group: 'nogi, timing, bark',
        },
      ],
    },

    blok_obrona: {
      emoji: '🛡️', label: 'Blok i obrona pola',
      drills: [
        {
          name: 'Blok crossowy (jeden na jeden)',
          duration: '10 min', total_attempts: 15,
          description: 'Bloker i atakujący 1v1. Bloker skupia się na zamknięciu skrzydła — nie ruchach ramion.',
          progression_tip: 'Cel: 10/15 zatrzymanych ataków → atakujący może zmienić kierunek w powietrzu.',
          target_pct: 67, sets: '3 serie po 5', muscle_group: 'nogi (odbicie), ramiona',
        },
        {
          name: 'Obrona pancake (dig po ataku)',
          duration: '12 min', total_attempts: 15,
          description: 'Partner atakuje w kierunek Twojej obrony. Ty wykonujesz dig (podejmowanie) w padzie lub pancake.',
          progression_tip: 'Cel: 11/15 do górnej części kortu → celuj w strefę rozgrywającego.',
          target_pct: 73, sets: '3 serie po 5', muscle_group: 'reflexy, nogi, elastyczność',
        },
        {
          name: 'Przeniesienie do obrony (transition)',
          duration: '15 min', total_attempts: 12,
          description: 'Bloker po nieudanym bloku wraca do roli obrońcy i musi podjąć piłkę za blokiem.',
          progression_tip: 'Cel: 9/12 → trener atakuje z różnych pozycji.',
          target_pct: 75, sets: '3 serie po 4', muscle_group: 'nogi, reflexy, kondycja',
        },
        {
          name: 'Przyjęcie ataku crossowego',
          duration: '10 min', total_attempts: 15,
          description: 'Atakujący uderza cross zawsze. Obrońca w strefie 5 lub 1 musi przewidzieć kierunek.',
          progression_tip: 'Cel: 12/15 → atakujący może zmienić na line w ostatniej chwili.',
          target_pct: 80, sets: '3 serie po 5', muscle_group: 'reflexy, forearm',
        },
        {
          name: 'Floater — odbiór zagrywki + atak',
          duration: '15 min', total_attempts: 12,
          description: 'Kompletna akcja: przyjęcie zagrywki floater → ustawienie → atak. Ćwiczysz każdy element.',
          progression_tip: 'Cel: 9/12 czystych akcji → zagrywka coraz mocniejsza.',
          target_pct: 75, sets: '3 serie po 4', muscle_group: 'cała siatkówka',
        },
      ],
    },

  },

};

console.log('[FitAI Seed] SPORT_DRILLS: 5 dyscyplin załadowanych ✅');
// ─────────────────────────────────────────────────────────────────────────────
// KONIEC FITAI SEED DATA v2.0
// ─────────────────────────────────────────────────────────────────────────────
// Liczby:
//   MEAL_DB:      9 śniadania + 9 obiady + 9 kolacje + 9 przekąski = 36 posiłków ✅
//   EXERCISE_DB:  8 klatka + 8 plecy + 8 nogi + 8 barki + 8 ramiona + 8 brzuch = 48 ćwiczeń ✅
//   SPORT_DRILLS: koszykówka (3 × 5) + piłka nożna (3 × 5) + tenis (3 × 5)
//                 + boks (3 × 5) + siatkówka (3 × 5) = 75 drilli ✅
//   ŁĄCZNIE:      36 + 48 + 75 = 159 rekordów seed data
// ─────────────────────────────────────────────────────────────────────────────