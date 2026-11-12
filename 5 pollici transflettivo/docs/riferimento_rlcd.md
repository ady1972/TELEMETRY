# Riferimento funzionale: RLCD TEST26

Base documentale: repository ady1972/TELEMETRY,
commit `2dd77edbf2b6fcee7a94dccad042567024c1441c`, directory
`firmware/rlcd-42/GOATS_RLCD_MG902_R12_1_SD_R14_2_TEST_26`.
Questi file rimangono intatti e non sono importati nel nuovo progetto.

| Ambito | Riferimento RLCD | Stato iniziale nel nuovo progetto |
|---|---|---|
| GNSS passivo | m9n_passive.h, goats_test_b.h | Nuovo parser NAV-PVT, RX17, nessun TX |
| Continuita' campioni | on_pvt, iTOW, duplicati | iTOW e istante ESP distinti, duplicati conteggiati |
| Racing | lambda display nel YAML RLCD | Contratto geometrico; renderer da sviluppare |
| Traguardo e riarmo | goats_laptimer.h::update | Da sviluppare e confrontare con tracce di riferimento |
| Intermedi/settore finale | update, complete_lap_ | Da sviluppare |
| LAST/BEST e giro minimo | complete_lap_ | Da sviluppare |
| Delta e filtro | calculate_live_delta_ | Da sviluppare |
| Passo gara/giri anomali | recompute_race_pace_ | Da sviluppare |
| Sessioni/recupero | goats_session_archive.h | Da sviluppare |
| CSV 25 Hz e SD | goats_gps_trace.h, goats_sd_storage.h | Da sviluppare, I/O fuori dal percorso GNSS |
| Pulsanti breve/lungo | goats_legacy_menu_ui.h | Da sviluppare per comandi fisici, nessun touch |
| Manager/USB | goats_test_b.h, goats_sd_usb_export.h | Da sviluppare su trasporto della nuova scheda |

## Regole per lo sviluppo

- Stesse priorita' visive RLCD: tempo corrente, LAST/BEST, delta, velocita',
  settori e stato GNSS. Non sostituire il riferimento con il layout Guition.
- Coordinate di riferimento 400x300; pannello destinazione 800x480. Il file
  layout_reference.h definisce la trasformazione iniziale x*2 e y*1.6.
  Il renderer dovra' scegliere font leggibili mantenendo gerarchia e proporzioni
  dei contenuti: il test card attuale non e' la GUI definitiva.
- Acquisire le epoche reali; non inventare campioni per raggiungere 25 Hz.
- Non modificare ricevitore, protocollo UBX, 230400 baud o frequenza attesa.
- Separare istante iTOW e orologio ESP. Non dichiarare il cronometraggio basato
  su iTOW solo perche' un parametro con quel nome e' disponibile.
- Testare traguardo e intermedi con replay deterministici prima delle prove in pista.
- Non fare scritture SD, stampe o attese nel consumatore GNSS.

## Limiti del riferimento da non nascondere

Nel motore RLCD TEST26, gnss_itow_ms viene ignorato e gli attraversamenti usano
now_ms senza interpolazione temporale. La direzione pista non viene applicata
dal motore condiviso. I filtri del passo gara non sono una validazione generale
di tutti i giri. Il nuovo scaffold non implementa ne' corregge queste parti.
Eventuali correzioni dovranno essere separate, documentate e verificate; non
vanno introdotte come modifiche implicite del porting.
