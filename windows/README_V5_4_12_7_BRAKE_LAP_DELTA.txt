GOATS RT Manager V5.4.12.8 - Brake Lap Delta

Modifica principale
- La colonna tempo delle tabelle frenata non indica più semplicemente il tempo locale della zona.
- Per ogni giro viene calcolato il Δ GIRO CUMULATIVO nello stesso punto fisico in cui inizia la frenata:
  negativo = giro avanti rispetto al riferimento; positivo = giro in ritardo.
- Resta il dato spaziale Frenata PRIMA/DOPO in metri, utile per capire la scelta del punto frenata.
- È aggiunto EFFETTO FRENATA: variazione del delta cumulativo tra ingresso e uscita della zona.
  negativo = la frenata/uscita ha fatto guadagnare tempo; positivo = ha fatto perdere tempo.
- Nel dettaglio Analisi Frenate vengono mostrati anche Δ giro uscita e tempo zona.
- Le tabelle fullscreen mostrano: Giro | Frenata | Δ giro | Effetto.
- Durante il replay la riga corrispondente continua a evidenziarsi.

Esempio
G8 | +4.2 m DOPO | -0.080 s AVANTI | +0.052 s PERSI
Significa: G8 frena 4.2 m più tardi; in quel punto è già 80 ms avanti, ma nella frenata+uscita perde 52 ms rispetto al giro di riferimento.

Calcolo
- Δ giro: confronto del tempo dal crossing di inizio giro allo stesso punto normalizzato della pista.
- Per i CSV diagnostici vengono usati gli start/end giro ricostruiti dal crossing iTOW.
- Effetto frenata = Δ giro uscita - Δ giro ingresso.

Invariati
- Tabelle laterali F1/F2/F3 in fullscreen.
- Replay Play/Pausa, 0.5x/1x, Reset ed ESC.
- Analisi frenate da velocità GNSS; nessun sensore pedale richiesto.
