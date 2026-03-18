# Metodologia di Predizione - Referendum Knowledge Graph

## Premessa

Questo strumento non e un sondaggio e non intende sostituirsi alle rilevazioni demoscopiche professionali. Si tratta di un aggregatore sperimentale che combina segnali pubblicamente disponibili per produrre una stima indicativa dell'orientamento elettorale. Le percentuali mostrate rappresentano la probabilita stimata dal modello, non una previsione del risultato.


## Architettura del modello

La predizione finale nasce dalla combinazione di quattro segnali indipendenti, ciascuno dotato di un peso e di un livello di confidenza proprio. L'approccio multi-segnale si ispira ai modelli ensemble (Dietterich, 2000) e agli aggregatori di sondaggi come quelli sviluppati da Nate Silver per FiveThirtyEight.


## Segnale 1: Sondaggi (peso 45%)

Aggrega i sondaggi disponibili con una media ponderata.

Ogni sondaggio viene pesato per recenza (decay esponenziale: il piu recente pesa 1.0, il precedente 0.8, poi 0.64, e cosi via) e per dimensione del campione (campioni superiori a 1000 unita pesano di piu).

La formula e:

    SI% = somma(si_pct * peso_recenza * peso_campione) / somma(pesi)

La confidenza cresce con il numero di sondaggi disponibili, fino a un massimo del 70%.

Fonti: sondaggi pre-caricati da Ipsos, SWG, EMG, Tecne, Euromedia, oltre a eventuali nuovi sondaggi estratti automaticamente dal testo degli articoli tramite pattern matching (per esempio "si 47%", "no 53%").

Limiti noti: i sondaggi sui referendum italiani hanno storicamente un errore medio di circa 13 punti percentuali. Nel referendum costituzionale del 2016 i sondaggi indicavano un intervallo 45-55, mentre il risultato fu 40.9 contro 59.1. Il modello ne tiene conto nell'intervallo di confidenza.

Riferimento: Ferrazza, Ferrazza (CISE/LUISS, 2026), "Perche i sondaggi sui referendum sono particolarmente inaffidabili".


## Segnale 2: Forza partitica (peso 25%)

Stima il bacino potenziale di SI e NO sulla base del consenso elettorale dei partiti schierati.

Si sommano le stime di consenso dei partiti favorevoli al SI (Fratelli d'Italia, Lega, Forza Italia, Noi Moderati, Azione, Italia Viva, per un totale di circa 52%) e di quelli favorevoli al NO (Partito Democratico, Movimento 5 Stelle, Alleanza Verdi e Sinistra, per un totale di circa 40.5%).

Il rapporto e:

    SI% = consenso_SI / (consenso_SI + consenso_NO)

La confidenza e fissata al 40% perche il voto partitico non si traduce linearmente nel voto referendario. Gli elettori possono votare in modo trasversale rispetto alle indicazioni del proprio partito, e l'astensione differenziata gioca un ruolo significativo.

Fonti: medie sondaggi sulle intenzioni di voto per le politiche (Supermedia YouTrend/AGI).

Limiti noti: nel referendum del 2016 circa il 20% degli elettori PD voto in dissenso con l'indicazione del partito. Per questo motivo il segnale ha volutamente la confidenza piu bassa tra i quattro.


## Segnale 3: Sentiment media (peso 20%)

Analizza il tono degli articoli raccolti da oltre 60 fonti per misurare l'orientamento prevalente della copertura mediatica.

Ogni articolo viene classificato come favorevole al SI, favorevole al NO, oppure neutro tramite keyword matching su un lessico di 187 termini in italiano e in inglese. Il lessico copre diverse categorie: verbi di azione ("approvare", "bocciare"), argomenti politici ("terzieta del giudice", "attacco alla magistratura"), posizioni esplicite ("vota si", "vota no") e riferimenti a trend ("cresce il no", "si in vantaggio").

La soglia di classificazione e bassa: basta un 5% di sbilanciamento tra keyword pro-SI e pro-NO perche l'articolo venga classificato come direzionale.

Il punteggio finale e ponderato per rilevanza dell'articolo (quante keyword legate al referendum contiene) e per forza del sentiment (quante keyword direzionali contiene). La formula e:

    SI% = 0.5 + (peso_SI - peso_NO) / (2 * peso_totale)

La confidenza e proporzionale alla copertura, cioe al rapporto tra articoli con sentiment chiaro e articoli totali.

Fonti: feed RSS di ANSA, Repubblica, Corriere della Sera, Il Sole 24 Ore, Sky TG24, Il Fatto Quotidiano, BBC, Euronews, e decine di ulteriori fonti scoperte automaticamente dal motore di discovery (Google News con 11 query diverse, Reddit, Guardian, Politico EU, fonti istituzionali come ANM e Altalex). In totale, oltre 60 feed gestiti da 5 agenti specializzati.

Limiti noti: il keyword matching non cattura ironia, contesto complesso o negazioni articolate. Una frase come "non e vero che la riforma sia positiva" verrebbe erroneamente classificata come favorevole al SI per la presenza della parola "positiva". Non si tratta di un modello di comprensione del linguaggio naturale. Inoltre, la copertura mediatica non riflette necessariamente l'opinione pubblica: i media hanno logiche proprie di selezione e framing delle notizie (agenda setting).

Riferimento: Liu, B. (2012) "Sentiment Analysis and Opinion Mining", Morgan & Claypool.


## Segnale 4: Momentum (peso 10%)

Misura se il sentiment si sta spostando verso SI o verso NO nel tempo.

Gli articoli vengono divisi in due meta temporali: recenti e meno recenti. Si calcola il sentiment medio di ciascuna meta, escludendo gli articoli neutri. La differenza (shift) tra le due medie indica la direzione del trend.

La formula e:

    SI% = 0.5 + shift * 0.3

Il coefficiente 0.3 smorza l'effetto per evitare reazioni eccessive a fluttuazioni di breve periodo. La confidenza e fissata al 25% data l'alta volatilita del segnale.

Limiti noti: con pochi articoli direzionali il segnale diventa rumoroso. Un singolo articolo molto polarizzato puo spostare la media in modo sproporzionato.


## Aggregazione finale

I quattro segnali vengono combinati con una media ponderata che tiene conto sia del peso base che della confidenza di ciascun segnale:

    Per ogni segnale:
        peso_effettivo = peso_base * confidenza

    SI_finale = somma(SI_segnale * peso_effettivo) / somma(pesi_effettivi)

In pratica, un segnale con alta confidenza conta di piu di uno con bassa confidenza, indipendentemente dal peso base assegnato. Per esempio, se i sondaggi hanno confidenza 60% e peso 45%, il loro peso effettivo e 0.27. Se il sentiment ha confidenza 68% e peso 20%, il suo peso effettivo e 0.136.

Questo meccanismo fa si che il modello si auto-calibri: quando i dati su un segnale sono scarsi o inaffidabili, quel segnale pesa meno nella predizione finale.


## Intervallo di confidenza

L'intervallo di confidenza e calibrato sull'errore storico dei sondaggi referendari italiani, che nel caso del 2016 fu di circa 13 punti percentuali.

La formula e:

    margine = 0.13 * (1 - confidenza_modello * 0.5)
    CI = [SI% - margine, SI% + margine]

Con una confidenza del modello al 53%, il margine risulta di circa 9.5 punti percentuali. Si tratta di un intervallo ampio, ma realistico per un referendum in cui l'incertezza e strutturalmente elevata.


## Limiti del modello e trasparenza

Il modello presenta diversi limiti di cui l'utente deve essere consapevole.

Non si tratta di un sondaggio demoscopico: non viene campionata la popolazione. L'analisi del sentiment si basa su keyword matching e non su modelli di intelligenza artificiale per la comprensione del linguaggio. I pesi dei segnali sono fissati a priori dall'autore e non calibrati su serie storiche. L'intervallo di confidenza e calibrato sul caso peggiore storico e non su un modello statistico formale.

Lo strumento e rilasciato come open source per garantire piena trasparenza e riproducibilita. Il codice sorgente e disponibile su GitHub e chiunque puo verificare, modificare o migliorare la metodologia.


## Riferimenti bibliografici

Dietterich, T. G. (2000). Ensemble Methods in Machine Learning. Multiple Classifier Systems, Springer.

Liu, B. (2012). Sentiment Analysis and Opinion Mining. Morgan & Claypool Publishers.

Silver, N. (2012). The Signal and the Noise: Why So Many Predictions Fail but Some Don't. Penguin Press.

CISE/LUISS (2026). Perche i sondaggi sui referendum sono particolarmente inaffidabili.

McCombs, M., Shaw, D. (1972). The Agenda-Setting Function of Mass Media. Public Opinion Quarterly, 36(2).


Mauro Fantin, 2026
