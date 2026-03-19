# Metodologia di Predizione - Referendum Knowledge Graph

## Premessa

Questo strumento non e un sondaggio e non intende sostituirsi alle rilevazioni demoscopiche professionali. Si tratta di un aggregatore sperimentale che combina segnali pubblicamente disponibili per produrre una stima indicativa dell'orientamento elettorale. Le percentuali mostrate rappresentano la probabilita stimata dal modello, non una previsione del risultato.


## Architettura del modello

La predizione finale nasce dalla combinazione di quattro segnali indipendenti (cinque quando disponibili gli exit poll), ciascuno dotato di un peso e di un livello di confidenza proprio. L'approccio multi-segnale si ispira ai modelli ensemble (Dietterich, 2000) e agli aggregatori di sondaggi come quelli sviluppati da Nate Silver per FiveThirtyEight.


## Segnale 1: Sondaggi (peso 45%, ridotto al 15% con exit poll)

Aggrega i sondaggi disponibili con una media ponderata.

Ogni sondaggio viene pesato per recenza (decay esponenziale: il piu recente pesa 1.0, il precedente 0.8, poi 0.64, e cosi via) e per dimensione del campione (campioni superiori a 1000 unita pesano di piu).

La formula e:

    SI% = somma(si_pct * peso_recenza * peso_campione) / somma(pesi)

La confidenza cresce con il numero di sondaggi disponibili, fino a un massimo del 70%.

Fonti: sondaggi pre-caricati da Ipsos, SWG, EMG, Tecne, Euromedia, oltre a eventuali nuovi sondaggi estratti automaticamente dal testo degli articoli tramite pattern matching (per esempio "si 47%", "no 53%").

Limiti noti: i sondaggi sui referendum italiani hanno storicamente un errore medio di circa 13 punti percentuali. Nel referendum costituzionale del 2016 i sondaggi indicavano un intervallo 45-55, mentre il risultato fu 40.9 contro 59.1. Il modello ne tiene conto nell'intervallo di confidenza.

Riferimento: Ferrazza, Ferrazza (CISE/LUISS, 2026), "Perche i sondaggi sui referendum sono particolarmente inaffidabili".


## Segnale 2: Forza partitica (peso 25%, ridotto al 10% con exit poll)

Stima il bacino potenziale di SI e NO sulla base del consenso elettorale dei partiti schierati.

Si sommano le stime di consenso dei partiti favorevoli al SI (Fratelli d'Italia, Lega, Forza Italia, Noi Moderati, Azione, Italia Viva, per un totale di circa 52%) e di quelli favorevoli al NO (Partito Democratico, Movimento 5 Stelle, Alleanza Verdi e Sinistra, per un totale di circa 40.5%).

Il rapporto e:

    SI% = consenso_SI / (consenso_SI + consenso_NO)

La confidenza e fissata al 40% perche il voto partitico non si traduce linearmente nel voto referendario. Gli elettori possono votare in modo trasversale rispetto alle indicazioni del proprio partito, e l'astensione differenziata gioca un ruolo significativo.

Fonti: medie sondaggi sulle intenzioni di voto per le politiche (Supermedia YouTrend/AGI).

Limiti noti: nel referendum del 2016 circa il 20% degli elettori PD voto in dissenso con l'indicazione del partito. Per questo motivo il segnale ha volutamente la confidenza piu bassa tra i quattro.


## Segnale 3: Sentiment media (peso 20%, ridotto al 15% con exit poll)

Analizza il tono degli articoli raccolti da oltre 70 fonti per misurare l'orientamento prevalente della copertura mediatica.

Ogni articolo viene classificato come favorevole al SI, favorevole al NO, oppure neutro tramite keyword matching su un lessico di oltre 200 termini in italiano e in inglese. Il lessico copre diverse categorie: verbi di azione ("approvare", "bocciare"), argomenti politici ("terzieta del giudice", "attacco alla magistratura"), posizioni esplicite ("vota si", "vota no"), riferimenti a trend ("cresce il no", "si in vantaggio") e indicatori di affluenza/partecipazione ("alta affluenza", "seggi vuoti", "astensionismo").

### Rilevamento delle negazioni

Il sistema include un meccanismo di rilevamento delle negazioni che migliora significativamente la precisione dell'analisi. Prima di contare un keyword come segnale SI o NO, il sistema verifica se nelle 4 parole precedenti compare una negazione (non, nessun, mai, senza, mica, neppure, nemmeno, neanche, e i corrispondenti inglesi). In caso positivo, il segnale viene invertito:

- "e una buona riforma" -> correttamente classificato come SI
- "non e una buona riforma" -> correttamente classificato come NO
- "non e pericolosa" -> correttamente classificato come SI (negazione di keyword NO)

La soglia di classificazione e bassa: basta un 5% di sbilanciamento tra keyword pro-SI e pro-NO perche l'articolo venga classificato come direzionale.

Il punteggio finale e ponderato per rilevanza dell'articolo (quante keyword legate al referendum contiene) e per forza del sentiment (quante keyword direzionali contiene). La formula e:

    SI% = 0.5 + (peso_SI - peso_NO) / (2 * peso_totale)

La confidenza e proporzionale alla copertura, cioe al rapporto tra articoli con sentiment chiaro e articoli totali.

Fonti: feed RSS di ANSA, Repubblica, Corriere della Sera, Il Sole 24 Ore, Sky TG24, Il Fatto Quotidiano, BBC, Euronews, e decine di ulteriori fonti scoperte automaticamente dal motore di discovery. In totale, oltre 80 feed gestiti da 6 agenti specializzati (vedi sezione Discovery Multi-Agente).

Limiti noti: il keyword matching, pur migliorato dal rilevamento delle negazioni, non cattura ironia, sarcasmo o contesti complessi con doppia negazione. Non si tratta di un modello di comprensione del linguaggio naturale. Inoltre, la copertura mediatica non riflette necessariamente l'opinione pubblica: i media hanno logiche proprie di selezione e framing delle notizie (agenda setting).

Riferimento: Liu, B. (2012) "Sentiment Analysis and Opinion Mining", Morgan & Claypool.


## Segnale 4: Momentum (peso 10%)

Misura se il sentiment si sta spostando verso SI o verso NO nel tempo, utilizzando un decay temporale esponenziale.

A differenza di un semplice split binario recente/vecchio, il momentum utilizza una curva di decadimento con emivita di 24 ore: ogni articolo viene pesato in base alla sua eta, con gli articoli piu recenti che contano progressivamente di piu. La formula di peso temporale e:

    peso_tempo = exp(-lambda * eta_in_secondi)

dove lambda = ln(2) / (24 * 3600), ovvero il peso si dimezza ogni 24 ore.

Gli articoli delle ultime 48 ore sono considerati "recenti" e confrontati con quelli precedenti. Lo shift tra il sentiment medio recente (ponderato) e quello precedente indica la direzione del trend.

La formula finale e:

    SI% = 0.5 + shift * 0.3

Il coefficiente 0.3 smorza l'effetto per evitare reazioni eccessive a fluttuazioni di breve periodo. La confidenza scala dinamicamente con il numero di articoli direzionali disponibili (fino a un massimo del 40%), invece di essere fissata staticamente.

Limiti noti: con pochi articoli direzionali il segnale diventa rumoroso. Un singolo articolo molto polarizzato puo spostare la media in modo sproporzionato, sebbene il decay temporale attenui questo effetto nel tempo.


## Segnale 5: Exit Poll (peso 50%, attivo solo dopo la chiusura dei seggi)

Questo segnale si attiva automaticamente dopo le ore 15:00 del 23 marzo 2026, quando i seggi chiudono e gli exit poll diventano disponibili. Quando attivo, ridistribuisce i pesi di tutti gli altri segnali per riflettere la maggiore affidabilita dei dati post-voto.

### Come funziona

Il sistema analizza gli articoli raccolti dai feed RSS alla ricerca di dati di exit poll e proiezioni. Utilizza tre pattern di estrazione complementari:

1. Percentuali dirette: "si 47,3%" / "no 52,7%"
2. Percentuali invertite: "47,3% per il si" / "52,7% per il no"
3. Range (forchette): "si tra 45 e 49" / "no tra 51 e 55" -> usa il punto medio

Ogni risultato viene classificato come exit poll o proiezione (piu affidabile). Le fonti riconosciute (Consorzio Opinio/Rai, Quorum-YouTrend/Sky TG24, Tecne/Mediaset, SWG/La7, Piepoli, EMG Different) ricevono un punteggio di affidabilita piu alto.

### Aggregazione

I risultati vengono aggregati con media ponderata per affidabilita della fonte:

    SI% = somma(si_pct * affidabilita) / somma(affidabilita)

La confidenza cresce con il numero e la qualita delle fonti, fino a un massimo del 90%.

### Ridistribuzione dei pesi

Quando gli exit poll sono disponibili, i pesi si riconfigurano automaticamente:

| Segnale          | Peso normale | Peso con exit poll |
|------------------|--------------|--------------------|
| Exit Poll        | -            | 50%                |
| Sondaggi         | 45%          | 15%                |
| Forza partitica  | 25%          | 10%                |
| Sentiment media  | 20%          | 15%                |
| Momentum         | 10%          | 10%                |

L'intervallo di confidenza si restringe significativamente (margine di errore ridotto al 30% del valore base) poiche gli exit poll sono storicamente piu accurati dei sondaggi pre-elettorali.

### Cruscotto visivo

Il tab Exit Poll presenta due gauge a lancetta affiancati (SI e NO):

- Prima della chiusura dei seggi: lancette ferme al 50%, barre grigie, messaggio di attesa con countdown
- Dopo la chiusura: gauge colorati con aggiornamento live, delta rispetto al 50%, dettaglio delle singole fonti rilevate e media ponderata

Limiti noti: l'estrazione dati dipende dalla pubblicazione di articoli con percentuali esplicite nei feed RSS. Se gli exit poll vengono comunicati solo in televisione o in formati non testuali, il sistema potrebbe non rilevarli immediatamente. Le proiezioni basate su scrutini reali sono piu affidabili degli exit poll iniziali.


## Discovery Multi-Agente

Il sistema utilizza 6 agenti specializzati che scandagliano la rete in parallelo per scoprire e validare nuove fonti di dati. Ogni agente copre un segmento diverso dell'ecosistema informativo:

| Agente                        | Fonti | Copertura |
|-------------------------------|-------|-----------|
| 1. Media italiani             | 19    | Testate nazionali e locali (AGI, Adnkronos, Rainews, Il Post, Avvenire, ecc.) |
| 2. Media internazionali       | 14    | Agenzie e testate estere (Reuters, Guardian, Politico EU, France24, DW, Al Jazeera, AP, Le Monde, El Pais) |
| 3. Google News (multi-query)  | 11    | Query mirate in italiano (8) e inglese (3) su referendum, riforma, sondaggi, affluenza |
| 4. Social & Community         | 5     | Reddit: r/italy, r/italypolitics, r/europe, r/worldnews |
| 5. Fonti istituzionali        | 5     | Camera dei Deputati, ANM, Altalex, Diritto.it, Questione Giustizia |
| 6. Exit Poll & Risultati      | 10    | Query Google News specifiche per exit poll, proiezioni, spoglio, risultati (IT+EN), con focus su Consorzio Opinio, YouTrend, Tecne, SWG |

Totale fonti candidate: oltre 80.

Ogni feed candidato viene validato automaticamente (parsing RSS, conteggio articoli, verifica rilevanza tramite keyword matching). Le fonti con almeno un articolo rilevante vengono classificate come "attive" e integrate nel Knowledge Graph e nella predizione.

L'Agente 6 (Exit Poll & Risultati) e progettato per attivarsi con massima efficacia dopo la chiusura dei seggi, cercando specificamente query come "exit poll referendum", "proiezioni referendum", "consorzio opinio", "youtrend proiezioni", "spoglio scrutinio" sia in italiano che in inglese.


## Aggregazione finale

I segnali vengono combinati con una media ponderata che tiene conto sia del peso base che della confidenza di ciascun segnale:

    Per ogni segnale:
        peso_effettivo = peso_base * confidenza

    SI_finale = somma(SI_segnale * peso_effettivo) / somma(pesi_effettivi)

In pratica, un segnale con alta confidenza conta di piu di uno con bassa confidenza, indipendentemente dal peso base assegnato. Per esempio, se i sondaggi hanno confidenza 60% e peso 45%, il loro peso effettivo e 0.27. Se il sentiment ha confidenza 68% e peso 20%, il suo peso effettivo e 0.136.

Questo meccanismo fa si che il modello si auto-calibri: quando i dati su un segnale sono scarsi o inaffidabili, quel segnale pesa meno nella predizione finale. Quando gli exit poll diventano disponibili, il modello si riconfigura automaticamente per dare loro il peso preponderante.


## Intervallo di confidenza

L'intervallo di confidenza e calibrato sull'errore storico dei sondaggi referendari italiani, che nel caso del 2016 fu di circa 13 punti percentuali.

La formula e:

    margine = errore_base * (1 - confidenza_modello * 0.5)
    CI = [SI% - margine, SI% + margine]

L'errore base e 0.13 in condizioni normali, ma viene ridotto a 0.039 (30% del valore) quando sono disponibili gli exit poll, poiche i dati post-voto hanno un margine di errore significativamente inferiore.

Con una confidenza del modello al 53%, il margine risulta di circa 9.5 punti percentuali in fase pre-voto. Con exit poll attivi e alta confidenza, il margine si riduce a 2-3 punti percentuali.


## Limiti del modello e trasparenza

Il modello presenta diversi limiti di cui l'utente deve essere consapevole.

Non si tratta di un sondaggio demoscopico: non viene campionata la popolazione. L'analisi del sentiment si basa su keyword matching con rilevamento delle negazioni, ma non su modelli di intelligenza artificiale per la comprensione del linguaggio. I pesi dei segnali sono fissati a priori dall'autore e non calibrati su serie storiche (sebbene si auto-calibrino tramite il meccanismo di confidenza). L'intervallo di confidenza e calibrato sul caso peggiore storico e non su un modello statistico formale.

Lo strumento e rilasciato come open source per garantire piena trasparenza e riproducibilita. Il codice sorgente e disponibile su GitHub e chiunque puo verificare, modificare o migliorare la metodologia.


## Riferimenti bibliografici

Dietterich, T. G. (2000). Ensemble Methods in Machine Learning. Multiple Classifier Systems, Springer.

Liu, B. (2012). Sentiment Analysis and Opinion Mining. Morgan & Claypool Publishers.

Silver, N. (2012). The Signal and the Noise: Why So Many Predictions Fail but Some Don't. Penguin Press.

CISE/LUISS (2026). Perche i sondaggi sui referendum sono particolarmente inaffidabili.

McCombs, M., Shaw, D. (1972). The Agenda-Setting Function of Mass Media. Public Opinion Quarterly, 36(2).

Mitofsky, W. J. (1991). A Short History of Exit Polls. In P. J. Lavrakas & J. K. Holley (Eds.), Polling and Presidential Election Coverage. Sage Publications.


Mauro Fantin, 2026
