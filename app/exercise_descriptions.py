"""
app/exercise_descriptions.py
FitAI – Słownik opisów ćwiczeń i drilli sportowych.

Klucze:  zawsze lowercase.
Wartość: krótki opis 3-5 zdań (na czym polega, jak wykonać poprawnie, na co uważać).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 1. ĆWICZENIA SIŁOWE / OGÓLNOROZWOJOWE
# ---------------------------------------------------------------------------

EXERCISE_HOW_TO: dict[str, str] = {
    # ── Klatka piersiowa ────────────────────────────────────────────────────
    "wyciskanie sztangi na ławce płaskiej": (
        "Połóż się na ławce, ściągnij łopatki i naciśnij stopy do podłogi. "
        "Opuszczaj sztangę kontrolowanie do dolnej klatki, łokcie pod kątem ~75° od tułowia. "
        "Wyciskaj dynamicznie, ale bez odbicia od klatki. "
        "Unikaj przeprostu w łokciach na szczycie ruchu."
    ),
    "wyciskanie hantli na ławce płaskiej": (
        "Kładąc się na ławce, unieś hantle na wyprostowane ramiona nad klatkę. "
        "Opuszczaj synchronicznie do poziomu klatki, zachowując lekki łuk w plecach. "
        "Wyciśnij z powrotem, zbliżając hantle ku sobie na szczycie. "
        "Nie pozwól, by ramiona schodzily poniżej poziomu ławki."
    ),
    "wyciskanie na ławce skośnej (incline press)": (
        "Ławka pod kątem 30-45°, sztanga opuszczana do górnej klatki. "
        "Łokcie lekko przed linią tułowia, nie rozchylaj ich zbytnio na boki. "
        "Ćwiczenie angażuje głównie górną klatką i przedni akton barku. "
        "Unikaj nadmiernego wyprostu lędźwi."
    ),
    "rozpiętki hantlami na ławce płaskiej": (
        "Unieś hantle nad klatkę z lekko ugiętymi łokciami. "
        "Opuszczaj w szerokim łuku aż do poziomu klatki, czując rozciąganie. "
        "Wróć ruchem ściskającym klatkę, nie prostując ramion całkowicie. "
        "Skup się na napięciu mięśniowym, nie na ciężarze."
    ),
    "pompki": (
        "Dłonie nieco szerzej niż barki, ciało tworzy sztywną deskę od głowy do pięt. "
        "Opuszczaj klatkę do kilku centymetrów od podłogi. "
        "Utrzymuj napięty brzuch i pośladki – nie pozwól, by biodra opadały lub unosiły się. "
        "Wydech podczas wycisku, wdech przy opuszczaniu."
    ),
    "wyciskanie sztangi leżąc": (
        "Połóż się na ławce płaskiej, ściągnij łopatki i naciśnij stopy mocno do podłogi. "
        "Opuszczaj sztangę kontrolowanie do dolnej części klatki, łokcie pod kątem ~45° od tułowia. "
        "Wyciśnij dynamicznie z wydechu, utrzymując lekki łuk w plecach i pięty na podłodze. "
        "Unikaj odbicia sztangi od klatki piersiowej i przeprostu łokci na szczycie ruchu."
    ),
    "wyciskanie hantli na skosie dodatnim": (
        "Ustaw ławkę pod kątem 30-45°, połóż się i unieś hantle na wyprostowane ramiona nad górną klatkę. "
        "Opuszczaj synchronicznie, prowadząc hantle po łuku ku górnej klatce – łokcie pod kątem ~75° od tułowia. "
        "Wyciśnij z powrotem, zbliżając hantle ku sobie na szczycie bez uderzania ich o siebie. "
        "Nie rozkładaj łokci zbyt szeroko – przeciąża stawy ramienne i zmniejsza zakres pracy klatki."
    ),
    "wyciskanie hantli na skosie ujemnym": (
        "Ustaw ławkę pod kątem ujemnym (-15° do -30°) i zabezpiecz stopy pod wałkiem. "
        "Unieś hantle na wyprostowane ramiona, następnie opuszczaj kontrolowanie nad dolną klatkę. "
        "Wyciśnij z wydechu, koncentrując napięcie na dolnej części mięśnia piersiowego większego. "
        "Zachowaj napięty brzuch przez cały ruch, by ustabilizować tułów na pochyłej ławce."
    ),
    "rozpiętki na maszynie (pec deck)": (
        "Usiądź na maszynie, ustaw oparcie tak by ramiona były równoległe do podłogi, a łokcie na podpórkach. "
        "Wykonuj ruch łączący ramiona przed sobą w szerokim łuku, skupiając się na ściskaniu klatki. "
        "Na końcu ruchu zatrzymaj dłonie obok siebie przez 1 sekundę, maksymalnie napinając mięsień piersiowy. "
        "Powoli wróć do pozycji wyjściowej – nie pozwól ciężarowi gwałtownie rozciągnąć stawu ramiennego."
    ),
    "rozpiętki na bramie (kabel dolny)": (
        "Ustaw karabińczyki kabli w dolnym położeniu, chwyć uchwyty i stań w rozkroku pośrodku bramy. "
        "Prowadź dłonie od bioder ku górze i przed siebie po szerokim łuku, jak gdybyś obejmował duże drzewo. "
        "Napnij klatkę na szczycie, zatrzymując ruch gdy dłonie spotkają się na poziomie klatki lub wyżej. "
        "Opuszczaj powoli z kontrolą, nie pozwalając ciężarom gwałtownie rozciągnąć ramion."
    ),
    "wyciskanie na maszynie hammera": (
        "Usiądź na maszynie, dopasuj oparcie i uchwyty do swojej sylwetki tak, by dłonie były na poziomie klatki. "
        "Wyciśnij uchwyty do przodu lub w górę pełnym zakresem ruchu, z wydechu napinając klatkę. "
        "Wróć wolno przez 3-4 sekundy – maszyna pozwala w pełni kontrolować fazę ekscentryczną. "
        "Idealne ćwiczenie finiszujące – bezpieczniejsze niż wolne ciężary, stosowane przy zmęczeniu mięśni."
    ),

    # ── Plecy ───────────────────────────────────────────────────────────────
    "martwy ciąg konwencjonalny": (
        "Stań z stopami na szerokość bioder, sztanga tuż nad stopami. "
        "Chwyć sztangę na szerokość barków, klatka wypięta, napnij brzuch. "
        "Wyprostuj biodra i kolana jednocześnie, trzymając sztangę blisko ciała. "
        "Nie zaokrąglaj dolnych pleców – to najważniejsza zasada bezpieczeństwa."
    ),
    "martwy ciąg": (
        "Stań z stopami na szerokość bioder, sztanga tuż nad stopami. "
        "Chwyć sztangę na szerokość barków, klatka wypięta, napnij brzuch. "
        "Wyprostuj biodra i kolana jednocześnie, trzymając sztangę blisko ciała. "
        "Nie zaokrąglaj dolnych pleców – to najważniejsza zasada bezpieczeństwa."
    ),
    "podciąganie nachwytem": (
        "Chwyć drążek nachwytem (dłonie od siebie) na szerokość barków lub szerzej. "
        "Rozpocznij od aktywnego zwisu – ściągnij łopatki w dół przed ruchem. "
        "Podciągaj do momentu, gdy klatka dotknie drążka, trzymając łokcie blisko tułowia. "
        "Opuszczaj powoli (3 sekundy) dla maksymalnego bodźca."
    ),
    "podciąganie podchwytem": (
        "Chwyć drążek podchwytem (dłonie ku sobie), wężej niż szerokość barków. "
        "Ściągnij łopatki, ugnij lekko kolana i skrzyżuj stopy. "
        "Podciągaj, kierując klatką ku drążkowi i angażując bicepsy. "
        "Pełny wyprost łokci w dolnej pozycji to klucz do pełnego zakresu ruchu."
    ),
    "pull-up": (
        "Chwyć drążek nachwytem na szerokość barków lub szerzej. "
        "Rozpocznij od aktywnego zwisu – ściągnij łopatki w dół przed ruchem. "
        "Podciągaj do momentu, gdy klatka dotknie drążka, trzymając łokcie blisko tułowia. "
        "Opuszczaj powoli (3 sekundy) dla maksymalnego bodźca."
    ),
    "wiosłowanie sztangą w opadzie tułowia": (
        "Pochyl tułów do ~45°, plecy proste, sztanga zwisa na wyprostowanych ramionach. "
        "Przyciągaj sztangę do pępka, ściskając łopatki razem na szczycie. "
        "Opuszczaj powoli, zachowując napięty brzuch przez cały ruch. "
        "Unikaj bujania tułowiem – to znak zbyt dużego ciężaru."
    ),
    "wiosłowanie hantlem jednostronnie": (
        "Oprzyj wolną rękę i kolano o ławkę, plecy równoległe do podłogi. "
        "Chwyć hantel, ugnij łokieć i przyciągnij do biodra. "
        "Łokieć blisko tułowia, pełny zakres ruchu z rozciągnięciem na dole. "
        "Nie rotuj tułowiem – ruch pochodzi wyłącznie z barku i łokcia."
    ),
    "wiosłowanie na maszynie siedząc (cable row)": (
        "Usiądź na maszynie, stopy na podpórkach, kolana lekko ugięte, chwyć uchwyt neutralnym lub pronacyjnym chwytem. "
        "Przyciągnij rączki do brzucha, ściskając łopatki razem na szczycie – tułów pozostaje pionowy bez bujania. "
        "Zatrzymaj się przez 1 sekundę z ściągniętymi łopatkami, maksymalnie napinając mięśnie pleców. "
        "Wróć kontrolowanie do wyprostu ramion, pozwalając łopatkom się rozchylić dla pełnego rozciągnięcia."
    ),
    "ściąganie drążka wyciągu do klatki (szeroki chwyt)": (
        "Usiądź przy wyciągu, uda zaciśnięte pod wałkiem, chwyć drążek szeroko nachwytem powyżej barków. "
        "Lekko odchyl tułów (ok. 15°) i ściągaj drążek łukiem do mostka, angażując mięśnie najszersze grzbietu. "
        "Na szczycie zatrzymaj ruch na 1 sekundę, mocno ściskając łopatki i napinając latissimusy. "
        "Wracaj powoli do wyprostu ramion, kontrolując rozciąganie – nie pozwól, by ciężar wyciągnął barki."
    ),
    "szrugsy ze sztangą (czworoboczny kapturowy)": (
        "Stań ze sztangą w dłoniach (chwyt na szerokość barków lub nieco szerzej), ramiona wyprostowane wzdłuż ciała. "
        "Unieś barki pionowo ku uszom możliwie wysoko, bez angażowania bicepsów ani rotacji barków. "
        "Zatrzymaj w górnej pozycji na 1-2 sekundy, maksymalnie napinając górną część czworobocznego. "
        "Opuszczaj powoli z kontrolą – unikaj okrężnych ruchów barkami, bo nie zwiększają efektywności, a przeciążają stawy."
    ),

    # ── Nogi ────────────────────────────────────────────────────────────────
    "przysiad ze sztangą": (
        "Sztanga na mięśniach czworobocznych (nie na kręgosłupie szyjnym). "
        "Cofnij biodra, zejdź co najmniej do równoległości ud do podłogi. "
        "Kolana podążają za stopami, pięty przez cały czas na podłodze. "
        "Wróć wypchnięciem przez pięty, utrzymując wypięta klatkę."
    ),
    "front squat": (
        "Sztanga spoczywa na przednich deltoidach (nie dłoniach). "
        "Łokcie wysoko przed tułowiem przez cały ruch. "
        "Zejdź głęboko przy wyprostowanym torsie – wymaga dobrej mobilności stawów skokowych. "
        "Angażuje silniej czworogłowe i gorset niż back squat."
    ),
    "rumuński martwy ciąg": (
        "Stój ze sztangą w dłoniach, plecy proste. "
        "Pochylaj tułów inicjując ruch biodrem, prowadź sztangę blisko ud. "
        "Zejdź aż poczujesz wyraźne rozciąganie w tylnych udach. "
        "Wróć napinając pośladki i prostując biodra – nie zaokrąglaj lędźwi."
    ),
    "wykroki bułgarskie": (
        "Tylna stopa spoczywa na ławce, przednia daleko przed ciałem. "
        "Opuszczaj biodra pionowo w dół, przednie kolano nad stopą. "
        "Odpychaj się przez piętę przedniej nogi przy powrocie. "
        "Zadbaj o stabilizację – drżenie kolana świadczy o zbyt dużym ciężarze."
    ),
    "leg press": (
        "Ustaw stopy na platformie na szerokość barków, lekko rozchylone. "
        "Opuszczaj platformę do kąta 90° w kolanach, nie dalej. "
        "Nie blokuj kolan na szczycie – utrzymuj lekkie ugięcie. "
        "Wyższe ustawienie stóp angażuje bardziej tylne uda i pośladki."
    ),
    "wspięcia na palce": (
        "Stań przodem do stopnia, pięty wystawione poza krawędź. "
        "Opuść pięty poniżej poziomu stopnia dla pełnego rozciągnięcia łydek. "
        "Unieś się na palce możliwie wysoko i zatrzymaj na 2 sekundy. "
        "Opuszczaj powoli – faza ekscentryczna buduje siłę łydek."
    ),
    "uginanie nóg leżąc": (
        "Połóż się na maszynie twarzą w dół, kostki pod rolką. "
        "Ugnij nogi do maksymalnego zakresu i zatrzymaj napięcie. "
        "Opuszczaj powoli przez 3-4 sekundy – ważna faza ekscentryczna. "
        "Unikaj unoszenia bioder od maszyny podczas ruchu."
    ),
    "wyprosty nóg na maszynie": (
        "Usiądź na maszynie, kostki przed rolką, oparcie na górach ud. "
        "Wyprostuj nogi do pełnego wyprostu i zatrzymaj się na 1 sekundę. "
        "Opuszczaj kontrolowanie, nie pozwalaj ciężarowi opaść. "
        "Dobre ćwiczenie izolacyjne na czworogłowe – stosuj jako uzupełnienie przysiadów."
    ),

    # ── Barki ───────────────────────────────────────────────────────────────
    "wyciskanie żołnierskie": (
        "Stój z sztangą na poziomie obojczyków, chwyt nieco szerzej niż barki. "
        "Wyciśnij pionowo nad głowę, lekko cofając głowę. "
        "Na szczycie nie blokuj łokci do końca i nie przeprostowuj lędźwi. "
        "Aktywny brzuch przez cały ruch chroni dolne plecy."
    ),
    "arnold press": (
        "Siedź na ławce, hantle trzymaj przed twarzą z dłońmi ku sobie. "
        "Wyciśnij ku górze, jednocześnie obracając dłonie na zewnątrz. "
        "Na szczycie dłonie są skierowane od ciebie, hantle nad głową. "
        "Ruch angażuje wszystkie trzy aktony barku i mięsień naramienny."
    ),
    "unoszenie hantli bokiem": (
        "Stój w lekkim opadzie, hantle przy biodrach z lekko ugiętymi łokciami. "
        "Unoś ramiona do poziomu barków (nie wyżej) – ruch lateralny. "
        "Zatrzymaj się na szczycie przez 1 sekundę. "
        "Unikaj szarpania i używania pędu – mały ciężar, czysta technika."
    ),
    "lateral raise": (
        "Stój w lekkim opadzie, hantle przy biodrach z lekko ugiętymi łokciami. "
        "Unoś ramiona do poziomu barków (nie wyżej) – ruch lateralny. "
        "Zatrzymaj się na szczycie przez 1 sekundę. "
        "Unikaj szarpania i używania pędu – mały ciężar, czysta technika."
    ),
    "face pull": (
        "Ustaw wyciąg na wysokości głowy z uchwytem linowym. "
        "Chwyć linę, cofnij się krok i przyciągaj ku twarzy z rotacją zewnętrzną. "
        "Łokcie uniesione do poziomu barków, dłonie za głową na szczycie. "
        "Kluczowe ćwiczenie profilaktyczne – regeneruje równowagę mięśniową barku."
    ),
    "wyciskanie hantli nad głowę siedząc": (
        "Usiądź na ławce z oparciem ustawionym pionowo lub lekko odchylonym, hantle trzymaj na poziomie barków z dłońmi skierowanymi do przodu. "
        "Wyciśnij hantle pionowo nad głowę, zbliżając je ku sobie na szczycie bez uderzania – łokcie lekko przed linią tułowia. "
        "Zatrzymaj się w górnej pozycji bez blokowania łokci i wróć kontrolowanie do pozycji wyjściowej. "
        "Aktywuj brzuch i dociskaj plecy do oparcia przez cały ruch – chroni to odcinek lędźwiowy."
    ),
    "unoszenie hantli przodem (front raise)": (
        "Stój lub siedź, hantle w dłoniach przy udach z lekko ugiętymi łokciami. "
        "Unoś ramiona naprzemiennie lub jednocześnie do przodu i ku górze, aż do poziomu oczu lub barków. "
        "Prowadź hantle z lekkim ugięciem w łokciu – nie prostuj ramion całkowicie, by zmniejszyć obciążenie stawu. "
        "Opuszczaj powoli i unikaj szarpania lub użycia pędu tułowia – izolujesz przedni akton barku."
    ),
    "odwrotne rozpiętki na maszynie (rear delt fly)": (
        "Usiądź przodem do maszyny i uchwyć rączki skrzyżowane lub wyprostowane, klatka oparta o podpórkę lub ugięta. "
        "Rozłóż ramiona poziomo w bok jak skrzydła, angażując tylny akton barku i tylne mięśnie naramienne. "
        "Na szczycie ruchu zatrzymaj się przez 1 sekundę, mocno ściskając łopatki i mięśnie tylnej części barku. "
        "Wróć powoli do pozycji wyjściowej – nie pozwól ciężarom opaść gwałtownie, bo tracisz napięcie mięśniowe."
    ),

    # ── Biceps ──────────────────────────────────────────────────────────────
    "uginania ze sztangą stojąc": (
        "Stój wyprostowany, sztanga w uchwycie podchwytem na szerokość barków. "
        "Ugnij łokcie, prowadząc sztangę ku ramionom – łokcie nieruchome przy boku. "
        "Zatrzymaj na szczycie, napinając bicepsy. "
        "Nie bujaj tułowiem – to ogranicza pracę bicepsa."
    ),
    "uginania hantlami naprzemiennie": (
        "Siedź lub stój, hantle w dłoniach zwróconych ku sobie. "
        "Ugnij jedną rękę, supinując (obracając) dłoń ku górze w trakcie ruchu. "
        "Zatrzymaj i powoli wróć, a następnie zmień rękę. "
        "Naprzemienność pozwala skupić się na każdym ramieniu osobno."
    ),
    "uginania młotkowe": (
        "Neutralny chwyt przez cały ruch (kciuk skierowany ku górze). "
        "Ugnij łokieć pionowo bez rotacji nadgarstka. "
        "Angażuje brachialis i brachioradialis bardziej niż klasyczne uginanie. "
        "Ćwicz powoli, unikając bujania tułowiem."
    ),
    "hammer curl": (
        "Neutralny chwyt przez cały ruch (kciuk skierowany ku górze). "
        "Ugnij łokieć pionowo bez rotacji nadgarstka. "
        "Angażuje brachialis i brachioradialis bardziej niż klasyczne uginanie. "
        "Ćwicz powoli, unikając bujania tułowiem."
    ),
    "uginania hantlem na modlitewniku (concentration curl)": (
        "Usiądź na ławce, oprzyj łokieć pracującej ręki o wewnętrzną stronę uda, hantel swobodnie zwisa w dół. "
        "Ugnij łokieć płynnym ruchem, prowadząc hantel ku ramionom – łokieć jest zablokowany przez udo, co eliminuje szarpanie. "
        "Zatrzymaj na szczycie przez 1 sekundę, maksymalnie napinając biceps, potem opuść powoli przez 3-4 sekundy. "
        "To ćwiczenie o największej izolacji bicepsa – stosuj niski ciężar i pełen zakres ruchu."
    ),
    "uginania na wyciągu (cable curl)": (
        "Stań przed wyciągiem dolnym, chwyć drążek lub uchwyt podchwytem na szerokość barków. "
        "Ugnij łokcie, prowadząc dłonie ku ramionom – łokcie nieruchome przy boku przez cały ruch. "
        "Wyciąg zapewnia stałe napięcie mięśniowe przez całą amplitudę, w odróżnieniu od hantli i sztangi. "
        "Wróć powoli do wyprostu, nie pozwalając ciężarowi wyciągnąć ramion – utrzymuj kontrolę przez pełny zakres."
    ),
    "spider curl na ławce skośnej": (
        "Połóż się klatką na ławce ustawionej pod kątem ~45°, ramiona zwisają swobodnie prostopadle do podłogi. "
        "Ugnij łokcie, prowadząc hantle lub sztangę ku twarzy – pozycja ciała uniemożliwia użycie rozmachu tułowia. "
        "Zatrzymaj na szczycie przez 1 sekundę i opuść powoli, czując pełne rozciągnięcie bicepsa w dolnej pozycji. "
        "Czysta izolacja bez możliwości bujania – stosuj mniejszy ciężar niż przy klasycznych ugięciach stojąc."
    ),

    # ── Triceps ─────────────────────────────────────────────────────────────
    "wyciskanie wąskim chwytem": (
        "Leż na ławce, chwyt na szerokość barków lub nieco węższy. "
        "Opuszczaj sztangę do dolnej klatki, łokcie blisko tułowia. "
        "Wyciśnij koncentrując pracę na tricepsach. "
        "Zbyt wąski chwyt przeciąża nadgarstki – nie przesadzaj z wąskością."
    ),
    "prostowanie ramion na wyciągu": (
        "Stań przed wyciągiem, chwyć drążek lub linę. "
        "Łokcie przy tułowiu, nie ruszają się – wyłącznie prostowanie przedramienia. "
        "Naciśnij do pełnego wyprostu i zatrzymaj, potem kontrolowanie wróć. "
        "To ćwiczenie izolacyjne – dbaj o brak ruchu łokci."
    ),
    "skull crushers": (
        "Leż na ławce, unieś sztangę/hantle nad klatkę. "
        "Zegnij łokcie opuszczając ciężar ku czołu lub za głowę. "
        "Wyciśnij z powrotem do wyprostu, angażując długą głowę tricepsa. "
        "Unikaj rozchylania łokci na boki – trzymaj je blisko siebie."
    ),
    "pompki na poręczach": (
        "Chwyć poręcze, unieś ciało na wyprostowanych ramionach. "
        "Pionowy tułów = więcej pracy tricepsa; pochylony = więcej klatki. "
        "Zejdź do kąta 90° w łokciach, odepchnij się do góry. "
        "Nie rozchylaj łokci i unikaj wychylania barków przed nadgarstki."
    ),
    "dips": (
        "Chwyć poręcze, unieś ciało na wyprostowanych ramionach. "
        "Pionowy tułów = więcej pracy tricepsa; pochylony = więcej klatki. "
        "Zejdź do kąta 90° w łokciach, odepchnij się do góry. "
        "Nie rozchylaj łokci i unikaj wychylania barków przed nadgarstki."
    ),
    "french press ze sztangą stojąc": (
        "Stój ze sztangą trzymaną oburącz nad głową na wyprostowanych ramionach, chwyt wąski lub na szerokość barków. "
        "Zegnij łokcie, opuszczając sztangę za głowę lub ku czołu, trzymając łokcie blisko siebie i bez rozchylania. "
        "Wyciśnij z powrotem do wyprostu, angażując długą głowę tricepsa, która jest w pełnym rozciągnięciu w dolnej pozycji. "
        "Aktywuj brzuch, by nie przeprostowywać lędźwi podczas ruchu – wariant stojący wymaga dobrej stabilizacji tułowia."
    ),
    "triceps kick-back hantlem": (
        "Pochyl tułów do ~45° lub oprzyj rękę i kolano o ławkę, łokieć pracującej ręki przy boku na poziomie tułowia. "
        "Wyprostuj ramię ku tyłowi do pełnego wyprostu łokcia, nie poruszając ramieniem ani tułowiem – izolujesz tricepsa. "
        "Zatrzymaj się przez 1 sekundę w wyproście, maksymalnie napinając boczną i środkową głowę tricepsa. "
        "Wróć powoli do kąta 90° w łokciu – nie pozwól, by hantel opadł swobodnie, bo tracisz bodźce ekscentryczne."
    ),

    # ── Brzuch / Core ───────────────────────────────────────────────────────
    "plank": (
        "Opar na przedramionach i palcach stóp, ciało tworzy prostą linię. "
        "Napnij brzuch, pośladki i uda jednocześnie. "
        "Trzymaj głowę w neutralnej pozycji, wzrok ku podłodze. "
        "Gdy biodra zaczynają opadać – przerwij serię."
    ),
    "plank przedni": (
        "Opar na przedramionach i palcach stóp, ciało tworzy prostą linię. "
        "Napnij brzuch, pośladki i uda jednocześnie. "
        "Trzymaj głowę w neutralnej pozycji, wzrok ku podłodze. "
        "Gdy biodra zaczynają opadać – przerwij serię."
    ),
    "dead bug": (
        "Leż na plecach, ramiona wyprostowane ku sufitowi, nogi zgięte pod 90°. "
        "Powoli opuszczaj naprzemiennie prawą rękę i lewą nogę. "
        "Przez cały ruch dociśnij dolne plecy do podłogi. "
        "Wróć do pozycji wyjściowej i powtórz na drugą stronę."
    ),
    "unoszenie nóg w zwisie": (
        "Chwyć drążek, ciało zwisa swobodnie. "
        "Unieś nogi (zgięte lub proste) siłą mięśni brzucha do poziomu bioder lub wyżej. "
        "Opuszczaj kontrolowanie – unikaj kołysania ciałem. "
        "Im prostsze nogi, tym trudniejsze ćwiczenie."
    ),
    "ab wheel": (
        "Klęcz na macie, trzymaj kółko oburącz przed sobą. "
        "Toczysz kółko wolno do przodu, utrzymując napięty brzuch i proste plecy. "
        "Dojedź tak daleko, jak możesz bez opadania bioder. "
        "Wróć kontrolując napięcie brzucha – nie używaj odskoku."
    ),
    "crunch na maszynie z linką": (
        "Klęknij lub stań przed wyciągiem górnym, chwyć linę lub drążek i trzymaj przy głowie lub ramionach. "
        "Zegnij kręgosłup ku dołowi angażując mięśnie prostych brzucha – ruch pochodzi z kręgosłupa, nie z bioder. "
        "Na szczycie zgięcia zatrzymaj się przez 1 sekundę, maksymalnie kurczą brzuch, potem wróć kontrolowanie. "
        "Stałe napięcie dzięki wyciągowi eliminuje martwe punkty – utrzymuj wolne tempo i nie ciągnij szyją."
    ),
    "hollow body hold": (
        "Leż na plecach, wyciągnij ręce za głowę i połącz nogi, a następnie unieś jednocześnie ramiona, łopatki i nogi nad podłogę. "
        "Wciśnij dolną część pleców mocno w podłogę – żadna szczelina między lędźwiami a matą przez cały czas trwania. "
        "Utrzymuj ciało w kształcie litery U odwróconej, napinając brzuch, pośladki i uda jednocześnie. "
        "Progresja: zacznij z nogami wyżej i rękami przy biodrach, stopniowo obniżaj nogi i wydłużaj ramiona gdy rosną siły."
    ),

    # ── Full body / olimpijskie ──────────────────────────────────────────────
    "kettlebell swing": (
        "Stój z kettlebell między stopami, plecy proste. "
        "Zamachu dokonujesz biodrami (hip hinge) – nie przysiadasz. "
        "Kettlebell wychyla się do poziomu barków mocą wyprostu bioder. "
        "Na szczycie napnij pośladki i brzuch, opuść kontrolując łańcuch ciągnięcia."
    ),
    "clean & press": (
        "Szybko podciągnij sztangę do poziomu ramion (clean). "
        "Bez zatrzymania wyciśnij nad głowę (press). "
        "Ćwiczenie balistyczne – wymaga koordynacji i eksplozywności. "
        "Opanuj clean i press osobno zanim połączysz je w jedno."
    ),
    "turkish get-up": (
        "Leż na plecach z kettlebell uniesionym w jednej ręce. "
        "Powoli przejdź przez każdy etap wstawania, utrzymując wzrok na dzwonku. "
        "Ćwiczenie poprawia mobilność, stabilizację i siłę funkcjonalną. "
        "Nie spieszysz się – kontroluj każdą fazę ruchu."
    ),
    "burpees": (
        "Z pozycji stojącej padnij do pompki, klatkę dotknij podłogi. "
        "Wróć do przysiadu, eksploduj do góry ze skokiem i klaśnięciem nad głową. "
        "Łącz siłę, cardio i koordynację w jednym ruchu. "
        "Utrzymuj rytm oddychania, nie wstrzymuj oddechu podczas pompki."
    ),
    "box jumps": (
        "Stań przed skrzynią w lekkim rozkroku. "
        "Dołek z zamachu ramion, eksploduj do góry i ląduj miękko na całej stopie. "
        "Unikaj lądowania wyłącznie na palcach – zwiększa ryzyko kontuzji ścięgna Achillesa. "
        "Ześnij ze skrzyni krokiem, nie skokiem."
    ),

    # ── Cardio ──────────────────────────────────────────────────────────────
    "interwały hiit na bieżni (30 s sprint / 90 s marsz)": (
        "Rozgrzej się 5 minut spokojnym marszem, następnie wykonaj 8 rund naprzemiennych: 30 sekund sprintu i 90 sekund marszu. "
        "W fazie sprintu utrzymuj tętno powyżej 85% HRmax – pełna moc, intensywne pompowanie ramionami. "
        "W fazie marszu aktywnie odpoczywaj, tętno spada poniżej 65% HRmax – nie stój, marsz utrzymuje metabolizm. "
        "Zakończ 5 minutami schładzającego marszu – gwałtowne zatrzymanie po HIIT zwiększa ryzyko zawrotów głowy."
    ),
    "ergometr wioślarski (steady state)": (
        "Usiądź na ergometrze, stopy w pasach, chwyć rączkę nachwytem i przyjmij pozycję startową: kolana ugięte, tułów lekko do przodu. "
        "Prowadź ruch sekwencyjnie: nogi → tułów → ręce w fazie pchania; ręce → tułów → nogi w fazie powrotu. "
        "Utrzymuj stałe tempo 500m split ~2:20-2:40, oddychaj rytmicznie: wydech przy ciągnięciu, wdech przy powrocie. "
        "Unikaj zaokrąglania pleców i nadmiernego odchylania tułowia – kręgosłup neutralny przez cały czas."
    ),
    "skakanka (double under lub single)": (
        "Stój z lekkim ugięciem kolan, skakanka za plecami, chwyt uchwytów swobodnie przy biodrach. "
        "Obroty wykonuj nadgarstkami (nie ramionami), skaczysz na palcach z minimalnym ugięciem kolan – odbij jak sprężyna. "
        "Single under: jedna rotacja na jeden skok; double under: dwa obroty skakanki na jeden wyskok – wymaga wyższego skoku i szybszych nadgarstków. "
        "Utrzymuj rytmiczny oddech i pionową postawę – garbienie się zaburza timing i prowadzi do potknięć."
    ),
    "atak rowerowy (assault bike) - tabata": (
        "Usiądź na assault bike, dopasuj wysokość siodełka tak by kolana były lekko ugięte w dolnym położeniu pedału. "
        "Wykonaj protokół Tabata: 8 rund po 20 sekund pełnej mocy (nogi i ręce jednocześnie) i 10 sekund odpoczynku. "
        "W fazie sprintu pompuj uchwyty i pedałuj z maksymalną mocą – assault bike opiera się tym mocniej, im szybciej pracujesz. "
        "W fazie odpoczynku trzymaj nogi i ręce nieruchomo lub pedałuj bardzo lekko – nie zsiadaj z roweru między rundami."
    ),
}


# ---------------------------------------------------------------------------
# 2. DRILLE SPORTOWE
# ---------------------------------------------------------------------------

DRILL_HOW_TO: dict[str, str] = {
    # ── Koszykówka – rzuty ───────────────────────────────────────────────────
    "rzuty osobiste": (
        "Stań za linią rzutów osobistych, stopy na szerokość barków. "
        "Trzymaj piłkę na palcach, nie na dłoni – kontrolujesz rotację backspin. "
        "Zgięcie w kolanach i łokciach, wyciśnij ku górze jednym płynnym ruchem. "
        "Utrzymaj dłoń w 'gęsiej szyi' po rzucie – to kluczowy element celności."
    ),
    "rzuty za 3 punkty": (
        "Ustaw się za łukiem w jednej z 5 pozycji (corners, wings, top). "
        "Przyjmij podanie z gotowości lub wyjdź zza zasłony w ruchu. "
        "Stopy zaplanowane przed rzutem – uniknij skręcania ciała podczas lotu piłki. "
        "Skup się na stałej mechnice rzutu, a nie na sile – za łukiem liczy się powtarzalność."
    ),
    "rzuty z odchylenia": (
        "Przyjmij piłkę w ruchu, zatrzymaj się skokiem obunóż lub krokiem. "
        "Odchylenie tułowia tworzy przestrzeń od obrońcy – nie przesadzaj z kątem. "
        "Utrzymuj wzrok na koszu przez cały czas rzutu. "
        "Ćwicz z obu stron i z różnych odległości mid-range."
    ),
    "mikan drill": (
        "Zacznij po lewej stronie tablicy, odbij piłkę i złap po drugiej stronie. "
        "Naprzemienne layupy z obu stron bez zbędnych kroków poza przepisowe 2. "
        "Skup się na miękkim dobiciu piłki w tablicę, nie na sile. "
        "Utrzymaj intensywny rytm – drill trenuje koordynację i technikę pod koszem."
    ),

    # ── Koszykówka – drybling ────────────────────────────────────────────────
    "figure-8 dribbling": (
        "Stój w rozkroku, piłka w jednej dłoni. "
        "Prowadź piłkę ósemką między nogami, przekazując ją z ręki do ręki. "
        "Utrzymuj niski środek ciężkości i wzrok przed siebie, nie na piłkę. "
        "Zwiększ prędkość wykonania gdy opanujesz podstawową formę."
    ),
    "stationary crossover": (
        "Stój w miejscu, piłka przed ciałem na wysokości kolan. "
        "Odbij piłkę crossoverem do drugiej ręki, ruch niski i szybki. "
        "Ćwicz 20 powtórzeń na każdą stronę w stałym rytmie. "
        "Progresja: wprowadź krok do przodu (live dribble) gdy opanujesz wariant statyczny."
    ),

    # ── Koszykówka – obrona ──────────────────────────────────────────────────
    "defensive slides": (
        "Przyjmij niską pozycję obronną: biodra cofnięte, kolana ugięte. "
        "Przesuń się bocznym krokiem bez krzyżowania nóg – utrzymuj dystans. "
        "Prowadząca stopa wysuwa się pierwsza, tylna dogania. "
        "Utrzymuj napięty gorset i niski środek ciężkości przez cały ruch."
    ),

    # ── Piłka nożna – podania ────────────────────────────────────────────────
    "podania krótkie": (
        "Uderz piłkę wewnętrzną stroną stopy – to daje precyzję. "
        "Stopa podporowa obok piłki, ciało ustawione w kierunku celu. "
        "Przenieś ciężar ciała na podporową nogę podczas uderzenia. "
        "Ćwicz podania z obu nóg i z różnych dystansów."
    ),
    "podania długie": (
        "Uderz piłkę grzbietem stopy (wrist area) lub stroną podbicia. "
        "Lekko ugięte kolano nogi uderającej, ciało lekko odchylone. "
        "Noga zamachowa przechodzi przez piłkę – follow-through decyduje o trajektorii. "
        "Ćwicz celność do stref, nie tylko moc uderzenia."
    ),
    "pierwsza piłka": (
        "Otwórz biodra i ciało w kierunku piłki podczas przyjęcia. "
        "Amortyzuj piłkę stopą lub udem – nie 'zbijaj', lecz 'chwytaj'. "
        "Pierwsza piłka powinna natychmiast ustawić cię do kolejnego ruchu. "
        "Ćwicz z partnerem lub o ścianę z różnych kątów."
    ),

    # ── Piłka nożna – technika ───────────────────────────────────────────────
    "zwody 1v1": (
        "Prowadź piłkę kontrolowanie w stronę obrońcy. "
        "Wykonaj zwód (np. sombrero, łamanie tempa) w momencie bliskiego kontaktu. "
        "Przyspiesz tuż po zwodzie – najważniejszy jest pierwszy krok po zmianie kierunku. "
        "Ćwicz zwody z obu nóg i na różnych prędkościach."
    ),
    "strzały na bramkę": (
        "Ustaw piłkę blisko nogi, uderzaj schodząc w kierunku bramki. "
        "Głowa nieruchoma nad piłką do momentu kontaktu – nie patrz na bramkę przed uderzeniem. "
        "Wybierz cel w bramce przed strzałem, nie podczas. "
        "Ćwicz z różnych pozycji: wewnątrz pola, na skrzydle, po dryblingu."
    ),
}


# ---------------------------------------------------------------------------
# 3. Pomocnicza funkcja lookup
# ---------------------------------------------------------------------------

def get_how_to(name: str, is_drill: bool = False) -> str:
    """
    Zwraca opis 'how_to' dla podanej nazwy ćwiczenia lub drilla.

    Algorytm:
      1. Sprawdź dokładne dopasowanie (exact match) po lowercase.
      2. Jeśli brak – sprawdź, czy któryś klucz w słowniku jest *zawarty* w name.lower()
         (substring fallback, np. 'Pull-up po jednym kozie' → klucz 'pull-up').
      3. Jeśli nadal brak – zwróć pusty string "".

    Args:
        name:     Nazwa ćwiczenia/drilla (dowolna wielkość liter).
        is_drill: True jeśli szukamy w DRILL_HOW_TO, False dla EXERCISE_HOW_TO.

    Returns:
        Opis str lub "" gdy brak wpisu.
    """
    lookup: dict[str, str] = DRILL_HOW_TO if is_drill else EXERCISE_HOW_TO
    key = name.strip().lower()

    # 1. Exact match
    if key in lookup:
        return lookup[key]

    # 2. Substring fallback – szukamy klucza zawartego w nazwie ćwiczenia
    for dict_key, description in lookup.items():
        if dict_key in key:
            return description

    # 3. Brak wpisu
    return ""