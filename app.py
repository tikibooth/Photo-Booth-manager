from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
import json
import os
import io

app = Flask(__name__)
app.config['SECRET_KEY'] = 'photobooth-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///photobooth.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─── MODELS ───────────────────────────────────────────────────────────────────

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200))
    telephone = db.Column(db.String(50))
    adresse = db.Column(db.Text)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    devis = db.relationship('Devis', backref='client', lazy=True, cascade='all, delete-orphan')

class Devis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(50), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    statut = db.Column(db.String(50), default='devis')  # devis, accepte, facture, paye, annule
    date_evenement = db.Column(db.Date)
    heure_debut = db.Column(db.String(10))
    heure_fin = db.Column(db.String(10))
    lieu = db.Column(db.String(300))
    type_evenement = db.Column(db.String(100))
    lignes = db.Column(db.Text, default='[]')  # JSON
    remise = db.Column(db.Float, default=0)
    acompte = db.Column(db.Float, default=0)
    commercial = db.Column(db.String(100), default="")
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def lignes_json(self):
        return json.loads(self.lignes or '[]')

    @property
    def sous_total(self):
        return sum(l.get('quantite', 1) * l.get('prix', 0) for l in self.lignes_json)

    @property
    def montant_remise(self):
        return self.sous_total * (self.remise / 100)

    @property
    def total(self):
        return self.sous_total - self.montant_remise

    @property
    def reste_a_payer(self):
        return self.total - (self.acompte or 0)

# ─── ROUTES PRINCIPALES ───────────────────────────────────────────────────────

@app.route('/')
def index():
    today = date.today()
    tous_devis = Devis.query.filter(Devis.statut.in_(['accepte', 'facture', 'paye'])).all()
    ca_total = sum(d.total for d in tous_devis)
    ca_paye = sum(d.total for d in Devis.query.filter_by(statut='paye').all())
    stats = {
        'total_clients': Client.query.count(),
        'devis_en_cours': Devis.query.filter_by(statut='devis').count(),
        'factures_impayees': Devis.query.filter_by(statut='facture').count(),
        'evenements_ce_mois': Devis.query.filter(
            Devis.date_evenement >= date(today.year, today.month, 1),
            Devis.statut.in_(['accepte', 'facture', 'paye'])
        ).count(),
        'ca_total': ca_total,
        'ca_paye': ca_paye,
    }

    prochains = Devis.query.filter(
        Devis.date_evenement >= today,
        Devis.statut.in_(['devis', 'accepte', 'facture'])
    ).order_by(Devis.date_evenement).limit(5).all()

    recents = Devis.query.order_by(Devis.created_at.desc()).limit(5).all()

    return render_template('index.html', stats=stats, prochains=prochains, recents=recents)

# ─── CLIENTS ──────────────────────────────────────────────────────────────────

@app.route('/clients')
def clients():
    clients = Client.query.order_by(Client.nom).all()
    return render_template('clients.html', clients=clients)

@app.route('/clients/nouveau', methods=['GET', 'POST'])
def nouveau_client():
    if request.method == 'POST':
        d = request.get_json()
        c = Client(
            nom=d['nom'], email=d.get('email',''),
            telephone=d.get('telephone',''), adresse=d.get('adresse',''),
            notes=d.get('notes','')
        )
        db.session.add(c)
        db.session.commit()
        return jsonify({'id': c.id, 'nom': c.nom})
    return render_template('client_form.html', client=None)

@app.route('/clients/<int:id>', methods=['GET'])
def voir_client(id):
    client = Client.query.get_or_404(id)
    return render_template('client_detail.html', client=client)

@app.route('/clients/<int:id>/modifier', methods=['GET', 'POST'])
def modifier_client(id):
    client = Client.query.get_or_404(id)
    if request.method == 'POST':
        d = request.get_json()
        client.nom = d['nom']
        client.email = d.get('email', '')
        client.telephone = d.get('telephone', '')
        client.adresse = d.get('adresse', '')
        client.notes = d.get('notes', '')
        db.session.commit()
        return jsonify({'success': True})
    return render_template('client_form.html', client=client)

@app.route('/clients/<int:id>/supprimer', methods=['DELETE'])
def supprimer_client(id):
    client = Client.query.get_or_404(id)
    db.session.delete(client)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/clients')
def api_clients():
    clients = Client.query.order_by(Client.nom).all()
    return jsonify([{'id': c.id, 'nom': c.nom, 'email': c.email, 'telephone': c.telephone} for c in clients])

# ─── DEVIS / FACTURES ─────────────────────────────────────────────────────────

def gen_numero(type='D'):
    today = date.today()
    prefix = f"{type}{today.year}{today.month:02d}"
    count = Devis.query.filter(Devis.numero.like(f"{prefix}%")).count()
    return f"{prefix}{count+1:03d}"

@app.route('/devis')
def liste_devis():
    statut = request.args.get('statut', 'tous')
    q = Devis.query
    if statut != 'tous':
        q = q.filter_by(statut=statut)
    devis = q.order_by(Devis.created_at.desc()).all()
    return render_template('liste_devis.html', devis=devis, statut_filtre=statut)

@app.route('/devis/nouveau', methods=['GET', 'POST'])
def nouveau_devis():
    if request.method == 'POST':
        d = request.get_json()
        numero = gen_numero('D')
        devis = Devis(
            numero=numero,
            client_id=d['client_id'],
            statut='devis',
            date_evenement=datetime.strptime(d['date_evenement'], '%Y-%m-%d').date() if d.get('date_evenement') else None,
            heure_debut=d.get('heure_debut', ''),
            heure_fin=d.get('heure_fin', ''),
            lieu=d.get('lieu', ''),
            type_evenement=d.get('type_evenement', ''),
            lignes=json.dumps(d.get('lignes', [])),
            remise=float(d.get('remise', 0)),
            acompte=float(d.get('acompte', 0)),
            commercial=d.get('commercial', ''),
            notes=d.get('notes', '')
        )
        db.session.add(devis)
        db.session.commit()
        return jsonify({'id': devis.id, 'numero': devis.numero})
    clients = Client.query.order_by(Client.nom).all()
    return render_template('devis_form.html', devis=None, clients=clients)

@app.route('/devis/<int:id>')
def voir_devis(id):
    devis = Devis.query.get_or_404(id)
    return render_template('voir_devis.html', devis=devis)

@app.route('/devis/<int:id>/modifier', methods=['GET', 'POST'])
def modifier_devis(id):
    devis = Devis.query.get_or_404(id)
    if request.method == 'POST':
        d = request.get_json()
        devis.client_id = d['client_id']
        devis.date_evenement = datetime.strptime(d['date_evenement'], '%Y-%m-%d').date() if d.get('date_evenement') else None
        devis.heure_debut = d.get('heure_debut', '')
        devis.heure_fin = d.get('heure_fin', '')
        devis.lieu = d.get('lieu', '')
        devis.type_evenement = d.get('type_evenement', '')
        devis.lignes = json.dumps(d.get('lignes', []))
        devis.remise = float(d.get('remise', 0))
        devis.acompte = float(d.get('acompte', 0))
        devis.commercial = d.get('commercial', '')
        devis.notes = d.get('notes', '')
        devis.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    clients = Client.query.order_by(Client.nom).all()
    return render_template('devis_form.html', devis=devis, clients=clients)

@app.route('/devis/<int:id>/statut', methods=['POST'])
def changer_statut(id):
    devis = Devis.query.get_or_404(id)
    d = request.get_json()
    nouveau = d['statut']
    # Si on passe en facture, changer le numéro
    if nouveau == 'facture' and devis.statut != 'facture':
        devis.numero = gen_numero('F')
    devis.statut = nouveau
    devis.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True, 'numero': devis.numero})

@app.route('/devis/<int:id>/supprimer', methods=['DELETE'])
def supprimer_devis(id):
    devis = Devis.query.get_or_404(id)
    db.session.delete(devis)
    db.session.commit()
    return jsonify({'success': True})

@app.route('/devis/<int:id>/pdf')
def generer_pdf(id):
    devis = Devis.query.get_or_404(id)
    html = render_template('pdf_template.html', devis=devis)
    try:
        from weasyprint import HTML
        pdf = HTML(string=html).write_pdf()
        return send_file(
            io.BytesIO(pdf),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"{devis.numero}.pdf"
        )
    except ImportError:
        return html, 200, {'Content-Type': 'text/html'}

# ─── CALENDRIER ───────────────────────────────────────────────────────────────

@app.route('/calendrier')
def calendrier():
    return render_template('calendrier.html')

@app.route('/api/evenements')
def api_evenements():
    devis = Devis.query.filter(Devis.date_evenement.isnot(None)).all()
    couleurs = {
        'devis': '#F59E0B',
        'accepte': '#3B82F6',
        'facture': '#8B5CF6',
        'paye': '#10B981',
        'annule': '#6B7280'
    }
    events = []
    for d in devis:
        events.append({
            'id': d.id,
            'title': f"{'📄' if d.statut=='devis' else '✅' if d.statut=='accepte' else '🧾' if d.statut=='facture' else '💚' if d.statut=='paye' else '❌'} {d.client.nom}",
            'start': d.date_evenement.isoformat(),
            'color': couleurs.get(d.statut, '#6B7280'),
            'url': f'/devis/{d.id}',
            'extendedProps': {
                'lieu': d.lieu,
                'type': d.type_evenement,
                'statut': d.statut,
                'total': d.total,
                'heure_debut': d.heure_debut,
                'heure_fin': d.heure_fin,
            }
        })
    return jsonify(events)

@app.route('/api/ical')
def export_ical():
    devis = Devis.query.filter(
        Devis.date_evenement.isnot(None),
        Devis.statut.in_(['devis', 'accepte', 'facture', 'paye'])
    ).all()
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//PhotoBooth Manager//FR',
        'CALSCALE:GREGORIAN',
        'X-WR-CALNAME:PhotoBooth Events',
    ]
    for d in devis:
        dt = d.date_evenement.strftime('%Y%m%d')
        lines += [
            'BEGIN:VEVENT',
            f'UID:{d.numero}@photobooth',
            f'DTSTART;VALUE=DATE:{dt}',
            f'DTEND;VALUE=DATE:{dt}',
            f'SUMMARY:[{d.statut.upper()}] {d.client.nom} - {d.type_evenement or "PhotoBooth"}',
            f'LOCATION:{d.lieu or ""}',
            f'DESCRIPTION:Devis {d.numero} - Total: {d.total:,.0f} XPF',
            'END:VEVENT',
        ]
    lines.append('END:VCALENDAR')
    content = '\r\n'.join(lines)
    return send_file(
        io.BytesIO(content.encode('utf-8')),
        mimetype='text/calendar',
        as_attachment=True,
        download_name='photobooth.ics'
    )

# ─── TABLEAU DE BORD API ──────────────────────────────────────────────────────

@app.route('/api/stats')
def api_stats():
    tous = Devis.query.filter(Devis.statut.in_(['accepte', 'facture', 'paye'])).all()
    par_mois = {}
    for d in tous:
        if d.date_evenement:
            key = f"{d.date_evenement.year}-{d.date_evenement.month:02d}"
            par_mois[key] = par_mois.get(key, 0) + d.total
    return jsonify({'par_mois': par_mois})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
