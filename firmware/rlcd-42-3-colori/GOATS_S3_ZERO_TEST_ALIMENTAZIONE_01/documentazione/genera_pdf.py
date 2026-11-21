"""Generate the two requested wiring PDFs. Requires reportlab (python -m pip install reportlab)."""
from pathlib import Path
import argparse
import subprocess
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable, KeepTogether
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4

HERE = Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--output-dir',type=Path,default=HERE)
args=parser.parse_args()
args.output_dir.mkdir(parents=True,exist_ok=True)
FONT=Path('/usr/share/fonts/truetype/open-sans')
if (FONT/'OpenSans-Regular.ttf').exists():
    pdfmetrics.registerFont(TTFont('Body',str(FONT/'OpenSans-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('BodyBold',str(FONT/'OpenSans-Bold.ttf')))
    pdfmetrics.registerFontFamily('Body',normal='Body',bold='BodyBold',italic='Body',boldItalic='BodyBold')
    normal,bold='Body','BodyBold'
else:
    normal,bold='Helvetica','Helvetica-Bold'
INK=colors.HexColor('#172A40'); ACCENT=colors.HexColor('#B72734'); LIGHT=colors.HexColor('#EFF3F7')
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleGoats',fontName=bold,fontSize=22,leading=27,textColor=INK,spaceAfter=7))
styles.add(ParagraphStyle(name='SubtitleGoats',fontName=normal,fontSize=10,leading=14,textColor=INK,spaceAfter=12))
styles.add(ParagraphStyle(name='SectionGoats',fontName=bold,fontSize=12,leading=16,textColor=INK,spaceBefore=10,spaceAfter=6))
styles.add(ParagraphStyle(name='BodyGoats',fontName=normal,fontSize=9,leading=13,textColor=INK,spaceAfter=7))
styles.add(ParagraphStyle(name='CellGoats',fontName=normal,fontSize=8.5,leading=11,textColor=INK))
styles.add(ParagraphStyle(name='HeaderGoats',fontName=bold,fontSize=8.5,leading=11,textColor=colors.white))
styles.add(ParagraphStyle(name='SmallGoats',fontName=normal,fontSize=7.5,leading=10,textColor=INK,spaceAfter=5))

def p(s,style='BodyGoats'):return Paragraph(s,styles[style])
def section(s):return p(s,'SectionGoats')
def table(rows,widths=None):
    data=[[p(str(c),'HeaderGoats' if i==0 else 'CellGoats') for c in row] for i,row in enumerate(rows)]
    t=Table(data,colWidths=widths or [170,180,165],hAlign='LEFT',repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),INK),('TEXTCOLOR',(0,0),(-1,0),colors.white),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),
        ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
        ('LINEBELOW',(0,-1),(-1,-1),0.6,colors.HexColor('#CAD3DC'))]))
    return t

class BlockDiagram(Flowable):
    def __init__(self,bench):super().__init__();self.bench=bench;self.width=515;self.height=100
    def draw(self):
        c=self.canv
        boxes=[(0,30,105,45,'USB','stessa porta/cavo'),(150,20,155,65,'S3-Zero 4 MB' if self.bench else 'ESP32-S3 16 MB','3V3 / GND comuni'),(350,52,165,40,'Osptek ST7306','SPI / 3,3 V'),(350,0,165,40,'MG902','solo VCC/GND' if self.bench else 'TX verso GPIO1')]
        for x,y,w,h,title,subtitle in boxes:
            c.setFillColor(LIGHT);c.setStrokeColor(INK);c.roundRect(x,y,w,h,6,fill=1,stroke=1)
            c.setFillColor(INK);c.setFont(bold,9);c.drawCentredString(x+w/2,y+h-16,title)
            c.setFont(normal,7.7);c.drawCentredString(x+w/2,y+11,subtitle)
        c.setStrokeColor(ACCENT);c.setLineWidth(1.4)
        c.line(105,52,150,52);c.line(305,70,350,70);c.line(305,35,328,35);c.line(328,35,328,20);c.line(328,20,350,20)
        if self.bench:
            c.setFillColor(ACCENT);c.setFont(bold,7);c.drawString(350,95,'GPS collegato solo nella prova B')

def footer(c,doc):
    c.saveState();w,h=A4
    c.setStrokeColor(colors.HexColor('#CAD3DC'));c.line(40,37,w-40,37)
    c.setFillColor(INK);c.setFont(normal,7)
    c.drawString(40,25,'GOATS RT  |  Collegamenti da sorgenti  |  21 novembre 2026')
    c.drawRightString(w-40,25,f'{doc.page}')
    c.restoreState()

def build(name,story,title):
    doc=SimpleDocTemplate(str(args.output_dir/name),pagesize=A4,rightMargin=40,leftMargin=40,topMargin=35,bottomMargin=49,
        title=title,author='GOATS RT',subject='Collegamenti e prova al banco; verifica hardware da eseguire')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)

base='https://github.com/ady1972/TELEMETRY'
issue=f'{base}/issues/33'
story=[p('TEST ALIMENTAZIONE 01','TitleGoats'),p('ESP32-S3-Zero · flash 4 MB · Osptek ST7306 a tre colori','SubtitleGoats'),
 p('Firmware diagnostico della issue #33. Il display mostra bianco/nero/rosso, secondi e causa del reset. GPS usato solo come carico: <b>nessuna UART e nessuna attesa del fix</b>.', 'BodyGoats'),BlockDiagram(True),
 section('1. Display verso Zero'),table([
 ['Segnale del display','Collegamento Zero','Nota'],['VCC / GND','3V3 / GND','Livelli a 3,3 V'],['CS','GPIO10','Chip select'],['DC','GPIO9','Dati / comandi'],['RESET / RST','GPIO8','Reset LCD'],['MOSI / DIN / SDA','GPIO11','SPI, non I2C'],['SCLK / CLK / SCL','GPIO12','SPI mode 0, 4 MHz'],['TE','Scollegato','Non richiesto']], [170,165,180]),
 section('2. GPS verso Zero: solo prova B'),table([
 ['Segnale MG902','Collegamento','Condizione'],['VCC','3V3 Zero','Prima verificare che il modulo accetti 3,3 V su VCC'],['GND','GND Zero','Massa comune'],['TX e RX','Entrambi scollegati','Fisicamente, per tutta la prova']], [170,165,180]),
 p('<b>Alimentazione:</b> USB della Zero. Modificare i collegamenti solo a USB rimossa. Nessun alimentatore esterno in parallelo. I numeri sono GPIO, non posizioni dei pin. Verificare le etichette della propria scheda.', 'BodyGoats'),
 PageBreak(),p('Prova A/B e primo flash','TitleGoats'),p('Stessa alimentazione USB, stesso cavo e stesso display in entrambe le condizioni.','SubtitleGoats'),
 section('3. Multimetro e sequenza di prova'),
 p('<b>Multimetro in volt continui:</b> puntale rosso, morsetto V, su 3V3 della Zero; puntale nero, morsetto COM, su GND. Non usare il morsetto corrente.'),
 p('<b>A — Solo display.</b> GPS completamente scollegato. Avvio a freddo tramite USB. Annotare tensione all’avvio e a regime; osservare il contatore per almeno 60 secondi.'),
 p('<b>B — Display + MG902.</b> Togliere USB, attendere lo spegnimento. Verificata la compatibilità VCC del modulo, collegare solo VCC e GND. TX e RX restano scollegati. Ripetere l’avvio a freddo con la stessa USB.'),
 p('<b>Ripetere A</b> se B fallisce. Un ritorno a zero indica un nuovo avvio; un’immagine ferma non prova che l’ESP32 sia ancora operativo. Se un componente si scalda in modo anomalo interrompere la prova.'),
 table([['Condizione','3V3 avvio / regime','Conteggio / reset / note'],['A: solo display','_____ / _____ V','________________________'],['B: display + MG902','_____ / _____ V','________________________'],['A ripetuta','_____ / _____ V','________________________']],[145,160,210]),
 p('La causa del reset è quella rilevata da ESP-IDF, con codice numerico. BROWNOUT suggerisce un calo di tensione; la sua assenza non lo esclude. Il multimetro può non vedere transitori rapidi. Il firmware non misura volt né corrente.'),
 section('4. Caricamento e file'),
 p('Nella cartella ESPHome affiancare <b>goats_s3_zero_test_alimentazione_01.yaml</b> e <b>GOATS_S3_ZERO_TEST_ALIMENTAZIONE_01/</b>. Aprire lo YAML esterno. Le dipendenze del display e i font sono locali.'),
 p('Per il primo flash USB usare <b>firmware.factory.bin a offset 0x0</b>, che include bootloader, partizioni e app. Con esptool 5: <font face="Courier">python -m esptool --chip esp32s3 --port COM5 write-flash 0x0 firmware.factory.bin</font>. Sostituire COM5 con la porta reale.'),
 p('Se necessario: tenere BOOT, premere e rilasciare RESET, poi rilasciare BOOT. Dopo il flash riavviare. Nessuna OTA. Il flash sostituisce il programma presente sulla scheda da banco.'),
 section('Riferimenti e limiti'),
 p(f'<link href="{issue}" color="#B72734">Issue #33 — requisiti e prova al banco</link>','SmallGoats'),
 p('Driver, reset LCD, rotazione e packing RBW derivati da GOATS_V0405_BOOT_FAST_FONT_TEST. Controlli software e build: vedere VERIFICA.md nel progetto consegnato. Prova elettrica e verifica sul pannello fisico ancora da eseguire.','SmallGoats')]
build('COLLEGAMENTI_TEST_ALIMENTAZIONE_01.pdf',story,'GOATS — Collegamenti TEST ALIMENTAZIONE 01')

full=f'{base}/blob/codex/rlcd-42-tricolore-v0405/firmware/rlcd-42-3-colori/GOATS_V0406_TEST26/README.md'
story=[p('RLCD 4.2 A TRE COLORI','TitleGoats'),p('Progetto completo V0.40.6 TEST26 · ESP32-S3 · flash 16 MB','SubtitleGoats'),
 p('<b>Configurazione del progetto completo:</b> flash 16 MB, ESP-IDF e GPIO38/39 accessibili per la SD. Questa guida non adatta il firmware alla Zero da 4 MB. Confermare flash e pin esposti sulla scheda reale.'),BlockDiagram(False),
 section('1. Display ST7306'),table([
 ['Segnale LCD','ESP32-S3','Nota'],['VCC / GND','3V3 / GND','Livelli 3,3 V'],['CS / DC / RESET','GPIO10 / GPIO9 / GPIO8','Rispettare questo ordine'],['MOSI / DIN / SDA','GPIO11','SPI, non I2C'],['SCLK / CLK / SCL','GPIO12','SPI mode 0, 4 MHz'],['TE','Scollegato','Non utilizzato']],[170,180,165]),
 section('2. GNSS MG902 / M9N'),table([
 ['Segnale GPS','ESP32-S3','Nota'],['TX GPS','GPIO1 (RX ESP)','Non il pin RX/UART0 serigrafato'],['RX GPS','Scollegato','Ricezione passiva: nessun TX ESP'],['GND','GND comune','Necessario per il segnale'],['VCC','Secondo la scheda MG902','3V3 solo se ammesso su VCC dal modulo']],[170,180,165]),
 p('<b>Impostazioni GPS richieste prima dell’uso:</b> UBX NAV-PVT a 25 Hz, 230400 baud, 8N1. TEST26 non configura il ricevitore. Le impostazioni in RAM della vecchia V0.40.5 possono perdersi senza alimentazione.'),
 section('3. Quattro pulsanti'),table([
 ['Tasto','GPIO','Collegamento'],['SU / GIÙ','GPIO4 / GPIO5','Ogni pulsante chiude verso GND'],['BACK / OK','GPIO6 / GPIO7','INPUT_PULLUP, nessun collegamento a 5 V']],[170,180,165]),
 p('GPIO4 è SU: non è disponibile come ingresso batteria. Questa versione non assegna un ADC né un partitore batteria.','SmallGoats'),
 PageBreak(),p('microSD, USB e avvio','TitleGoats'),p('Collegamenti del firmware V0.40.6 TEST26 completo','SubtitleGoats'),
 section('4. microSD nativa: SDMMC a 1 bit'),table([
 ['Contatto microSD','Segnale','Collegamento'],['1','DAT2','Pull-up 10 kΩ a 3V3'],['2','DAT3 / CS','Pull-up 10 kΩ a 3V3, non CS SPI'],['3','CMD','GPIO21 + pull-up 10 kΩ a 3V3'],['4','VDD','3,3 V'],['5','CLK','GPIO38, nessun pull-up richiesto'],['6','VSS','GND'],['7','DAT0','GPIO39 + pull-up 10 kΩ a 3V3'],['8','DAT1','Pull-up 10 kΩ a 3V3']],[145,130,240]),
 p('Numerazione dei contatti della <b>scheda microSD</b>, non del connettore di un modulo generico. Verificare lo schema del socket. I pull-up possono essere già presenti. Usare 100 nF + 10 µF vicini al socket tra 3V3 e GND.'),
 p('La SD <b>non condivide lo SPI del display</b>. Un modulo con i soli segnali SPI può non esporre DAT1/DAT2 e richiede una verifica dello schema. Usare FAT32. Il mount avviene al primo fix valido o su richiesta USB.'),
 section('5. USB dati nativa e alimentazione'),table([
 ['Funzione','Collegamento','Nota'],['USB D− / D+','GPIO19 / GPIO20','Usare la porta nativa ESP32-S3'],['USB GND','GND comune','VBUS secondo lo schema della scheda'],['USB via CH340 / CP210x','Non equivale alla USB nativa','Non fornisce Manager / MSC']],[145,180,190]),
 p('Se la porta nativa è già cablata sulla scheda, usare quel connettore. Non aggiungere collegamenti VBUS senza lo schema. Evitare alimentazioni in conflitto. In modalità disco USB il PC possiede la SD: espellere dal sistema operativo prima di riavviare.'),
 section('6. Prima dell’uso'),
 p('Controllare continuità e polarità a dispositivo spento, GPIO esposti, alimentazione e capacità della flash. Avviare prima con il solo display; aggiungere i moduli a dispositivo spento. Verificare GPS, pulsanti, salvataggio su SD e trasferimento USB.'),
 p('Il progetto di questo branch si apre da <b>GOATS_V0406_TEST26/goats_42_color_v0406_test26.yaml</b>, mantenendo tutte le sue dipendenze. Il layout flash differisce dalla V0.40.5: esportare i dati prima di un cambio firmware.'),
 p(f'<link href="{full}" color="#B72734">Sorgente del pinout — README V0.40.6 TEST26 nel branch di riferimento</link>','SmallGoats'),
 p('Pinout verificato sui sorgenti di questo branch; collegamenti e funzionamento sul dispositivo reale restano da collaudare. Nessun flash né prova elettrica eseguiti con la consegna della issue #33.','SmallGoats')]
build('COLLEGAMENTI_RLCD_42_COLOR_TEST26.pdf',story,'GOATS — Collegamenti RLCD 4.2 COLOR TEST26')
print('Generated two wiring PDFs in',args.output_dir)
