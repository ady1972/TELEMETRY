GOATS RT Manager V5.4.11.9 - TIMING CROSSING FIX

- Conserva nel database iTOW, nav_seq, frequenze diagnostiche e finish_signed_m dei CSV V12.0.5+.
- Ricostruisce i tempi giro sul vero crossing della finish line tramite interpolazione fra i due fix a cavallo dello zero.
- Usa iTOW GNSS come base tempi quando disponibile, con gestione rollover settimanale.
- Stima il crossing iniziale con breve extrapolazione dai primi campioni subito dopo il traguardo.
- Reimportando lo stesso CSV aggiorna la sessione in-place, senza duplicarla e senza perdere le note.
- I CSV più vecchi senza colonne diagnostiche restano compatibili con il metodo precedente.
