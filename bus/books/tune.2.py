"""
Online-Adaptive PID-Regelung
=============================
Der Regler passt seine Parameter (Kp, Ki, Kd) während des Betriebs an,
basierend auf dem aktuellen Systemverhalten.
"""

import numpy as np
import matplotlib.pyplot as plt
from collections import deque
import time
from dataclasses import dataclass
from enum import Enum
import threading
import warnings

# ============================================================================
# ADAPTIONSSTRATEGIEN
# ============================================================================

class AdaptionsModus(Enum):
    """Verschiedene Online-Adaptionsstrategien"""
    GRADIENT = 1        # Gradientenabstieg
    MRAC = 2            # Model Reference Adaptive Control
    SELBSTTUNING = 3    # Regelbasierte Selbstoptimierung
    HYBRID = 4          # Kombination mehrerer Strategien
    GA = 5              # Genetischer Algorithmus (periodisch)


@dataclass
class AdaptionsParameter:
    """Parameter für die Online-Adaption"""
    lernrate: float = 0.01
    vergessensfaktor: float = 0.95
    adaptions_intervall: int = 10
    minimal_aenderung: float = 0.001
    maximal_aenderung: float = 0.5


class OnlineAdaptiverPID:
    """
    PID-Regler mit Online-Adaption der Parameter
    
    Features:
    - Kontinuierliche Anpassung während des Betriebs
    - Verschiedene Adaptionsstrategien
    - Anti-Windup und Stellgrößenbegrenzung
    - Rauschfilterung für Ableitung
    - Performance-Monitoring
    """
    
    def __init__(self, 
                 Kp_start: float = 1.0,
                 Ki_start: float = 0.1,
                 Kd_start: float = 0.05,
                 setpoint: float = 0,
                 sample_time: float = 0.01,
                 output_limits: tuple = (None, None),
                 modus: AdaptionsModus = AdaptionsModus.HYBRID):
        """
        Initialisiert den online-adaptiven PID-Regler
        
        Args:
            Kp_start: Startwert Proportionalverstärkung
            Ki_start: Startwert Integralverstärkung
            Kd_start: Startwert Differenzialverstärkung
            setpoint: Sollwert
            sample_time: Abtastzeit in Sekunden
            output_limits: (min, max) für Stellgrößenbegrenzung
            modus: Adaptionsmodus
        """
        # PID-Parameter
        self.Kp = Kp_start
        self.Ki = Ki_start
        self.Kd = Kd_start
        
        self.Kp_start = Kp_start
        self.Ki_start = Ki_start
        self.Kd_start = Kd_start
        
        self.setpoint = setpoint
        self.sample_time = sample_time
        self.output_limits = output_limits
        self.modus = modus
        
        # Interne Zustände
        self.last_error = 0
        self.integral = 0
        self.last_output = 0
        self.last_time = time.time()
        
        # Filter für Ableitung (Tiefpass)
        self.derivative_filter = 0.1
        self.filtered_derivative = 0
        self.derivative_buffer = deque(maxlen=5)
        
        # Anti-Windup
        self.integral_limit = None
        self.anti_windup = True
        
        # Adaptions-Parameter
        self.adapt_params = AdaptionsParameter()
        self.adaptions_schritt = 0
        
        # Historien für Analyse
        self.error_history = deque(maxlen=1000)
        self.output_history = deque(maxlen=1000)
        self.time_history = deque(maxlen=1000)
        self.Kp_history = deque(maxlen=1000)
        self.Ki_history = deque(maxlen=1000)
        self.Kd_history = deque(maxlen=1000)
        self.setpoint_history = deque(maxlen=1000)
        
        # Für MRAC
        self.reference_model = None
        self.reference_output = 0
        
        # Für Gradientenverfahren
        self.gradient_Kp = 0
        self.gradient_Ki = 0
        self.gradient_Kd = 0
        
        # Performance-Metriken
        self.performance_metrics = {
            'mse': deque(maxlen=100),
            'ueberschwingen': deque(maxlen=10),
            'stellaktivitaet': deque(maxlen=100)
        }
        
        # Statistik
        self.adaptions_count = 0
        self.last_adaptation_time = time.time()
        
    def calculate(self, feedback: float, current_time: float = None) -> float:
        """
        Berechnet die Stellgröße und führt Online-Adaption durch
        
        Args:
            feedback: Aktueller Messwert (Regelgröße)
            current_time: Aktuelle Zeit (optional)
            
        Returns:
            Stellgröße
        """
        if current_time is None:
            current_time = time.time()
        
        dt = current_time - self.last_time
        
        if dt >= self.sample_time:
            # Fehler berechnen
            error = self.setpoint - feedback[0] if isinstance(feedback, tuple) else feedback
            self.error_history.append(error)
            self.time_history.append(current_time)
            self.setpoint_history.append(self.setpoint)
            
            # Integral mit Anti-Windup
            self.integral += error * dt
            if self.anti_windup and self.integral_limit:
                self.integral = np.clip(self.integral, 
                                       -self.integral_limit, 
                                       self.integral_limit)
            
            # Ableitung mit Filterung
            derivative = (error - self.last_error) / dt
            self.derivative_buffer.append(derivative)
            self.filtered_derivative = np.mean(self.derivative_buffer)
            
            # PID-Ausgang berechnen
            output = (self.Kp * error + 
                     self.Ki * self.integral + 
                     self.Kd * self.filtered_derivative)
            
            # Stellgrößenbegrenzung
            if self.output_limits[0] is not None:
                output = max(self.output_limits[0], output)
            if self.output_limits[1] is not None:
                output = min(self.output_limits[1], output)
            
            # Zustände aktualisieren
            self.last_error = error
            self.last_time = current_time
            self.last_output = output
            self.output_history.append(output)
            
            # Parameter speichern
            self.Kp_history.append(self.Kp)
            self.Ki_history.append(self.Ki)
            self.Kd_history.append(self.Kd)
            
            # ONLINE-ADAPTION DURCHFÜHREN
            self.adaptions_schritt += 1
            if self.adaptions_schritt % self.adapt_params.adaptions_intervall == 0:
                self._online_adaption(error, dt)
            
            return output
        
        self.last_time = current_time
        return self.last_output
    
    def _online_adaption(self, error: float, dt: float):
        """
        Führt die Online-Adaption basierend auf dem gewählten Modus durch
        """
        if self.modus == AdaptionsModus.GRADIENT:
            self._gradient_adaption(error, dt)
        elif self.modus == AdaptionsModus.MRAC:
            self._mrac_adaption(error, dt)
        elif self.modus == AdaptionsModus.SELBSTTUNING:
            self._selbsttuning_adaption(error, dt)
        elif self.modus == AdaptionsModus.HYBRID:
            self._hybrid_adaption(error, dt)
        elif self.modus == AdaptionsModus.GA:
            self._ga_adaption(error, dt)
        
        # Parameter begrenzen
        self._clamp_parameters()
        
        self.adaptions_count += 1
    
    def _gradient_adaption(self, error: float, dt: float):
        """
        Gradientenbasierte Online-Adaption
        Verwendet den momentanen Fehler zur Parameteranpassung
        """
        # Gradienten schätzen (vereinfachtes Verfahren)
        self.gradient_Kp = -error * error
        self.gradient_Ki = -error * self.integral
        self.gradient_Kd = -error * self.filtered_derivative
        
        # Parameter aktualisieren (steepest descent)
        lr = self.adapt_params.lernrate
        
        # Adaptive Lernrate basierend auf Fehlergröße
        fehler_norm = abs(error) / (abs(self.setpoint) + 1e-6)
        adaptive_lr = lr * (1 + fehler_norm)
        
        self.Kp += adaptive_lr * self.gradient_Kp * dt
        self.Ki += adaptive_lr * self.gradient_Ki * dt
        self.Kd += adaptive_lr * self.gradient_Kd * dt
    
    def _mrac_adaption(self, error: float, dt: float):
        """
        Model Reference Adaptive Control (MRAC)
        Benötigt ein Referenzmodell für das gewünschte Verhalten
        """
        if self.reference_model is None:
            # Standard-Referenzmodell: PT2 mit gutem Verhalten
            self.reference_model = lambda sp: self._pt2_reference(sp)
        
        # Referenzausgang berechnen
        self.reference_output = self.reference_model(self.setpoint)
        
        # Fehler zwischen Referenz und aktuellem System
        model_error = self.reference_output - (self.setpoint - error)
        
        # MIT-Regel für Parameter-Adaption
        gamma = self.adapt_params.lernrate * 0.1
        
        self.Kp += gamma * model_error * error * dt
        self.Ki += gamma * model_error * self.integral * dt
        self.Kd += gamma * model_error * self.filtered_derivative * dt
    
    def _selbsttuning_adaption(self, error: float, dt: float):
        """
        Regelbasierte Selbstoptimierung
        Verwendet Heuristiken zur Parameteranpassung
        """
        if len(self.error_history) < 20:
            return
        
        # Letzte Fehler analysieren
        recent_errors = list(self.error_history)[-20:]
        error_mean = np.mean(np.abs(recent_errors))
        error_std = np.std(recent_errors)
        error_trend = np.polyfit(range(len(recent_errors)), recent_errors, 1)[0]
        
        # Oszillation erkennen (Vorzeichenwechsel)
        zero_crossings = sum(1 for i in range(1, len(recent_errors)) 
                           if recent_errors[i-1] * recent_errors[i] < 0)
        
        # Performance-Metriken aktualisieren
        mse = np.mean(np.array(recent_errors)**2)
        self.performance_metrics['mse'].append(mse)
        
        # Heuristische Regeln für Parameteranpassung
        alte_Kp, alte_Ki, alte_Kd = self.Kp, self.Ki, self.Kd
        
        # Regel 1: Oszillation -> Kp reduzieren, Kd erhöhen
        if zero_crossings > 5 and error_std > 0.1 * abs(self.setpoint):
            self.Kp *= 0.95
            self.Kd *= 1.05
            if len(self.performance_metrics['ueberschwingen']) < 10:
                self.performance_metrics['ueberschwingen'].append(error_std)
        
        # Regel 2: Anhaltender Fehler -> Kp erhöhen, Ki anpassen
        elif abs(error_trend) < 0.001 and error_mean > 0.05 * abs(self.setpoint):
            self.Kp *= 1.02
            self.Ki *= 1.01
        
        # Regel 3: Im eingeschwungenen Zustand -> Ki optimieren
        elif error_mean < 0.01 * abs(self.setpoint) and len(recent_errors) > 10:
            if abs(np.mean(recent_errors[-5:])) > abs(np.mean(recent_errors[:5])):
                # Fehler wird größer -> Ki reduzieren
                self.Ki *= 0.99
            else:
                # Fehler bleibt klein -> Ki leicht erhöhen für bessere Führung
                self.Ki *= 1.005
        
        # Regel 4: Stellgrößenaktivität überwachen
        if len(self.output_history) > 20:
            stell_aktivitaet = np.std(list(self.output_history)[-20:])
            self.performance_metrics['stellaktivitaet'].append(stell_aktivitaet)
            
            if stell_aktivitaet > 10 * error_std:  # Zu aktive Stellgröße
                self.Kd *= 1.02  # Mehr Dämpfung
                self.Kp *= 0.99  # Weniger Verstärkung
        
        # Änderungen begrenzen
        for param, alter_wert in [('Kp', alte_Kp), ('Ki', alte_Ki), ('Kd', alte_Kd)]:
            aenderung = abs(getattr(self, param) - alter_wert)
            if aenderung > self.adapt_params.maximal_aenderung:
                setattr(self, param, alter_wert + self.adapt_params.maximal_aenderung * 
                       (1 if getattr(self, param) > alter_wert else -1))
    
    def _hybrid_adaption(self, error: float, dt: float):
        """
        Hybride Adaption: Kombiniert mehrere Strategien
        """
        # Gradientenbasierte Feinkorrektur
        self._gradient_adaption(error, dt)
        
        # Periodisch (alle 10 Schritte) regelbasiert nachjustieren
        if self.adaptions_schritt % (self.adapt_params.adaptions_intervall * 10) == 0:
            alte_Kp, alte_Ki, alte_Kd = self.Kp, self.Ki, self.Kd
            self._selbsttuning_adaption(error, dt)
            
            # Sanfte Übernahme
            self.Kp = 0.7 * alte_Kp + 0.3 * self.Kp
            self.Ki = 0.7 * alte_Ki + 0.3 * self.Ki
            self.Kd = 0.7 * alte_Kd + 0.3 * self.Kd
    
    def _ga_adaption(self, error: float, dt: float):
        """
        Periodische Optimierung mit genetischem Algorithmus
        (nur alle N Schritte, da rechenintensiv)
        """
        # Nur alle 500 Schritte ausführen
        if self.adaptions_schritt % 500 != 0:
            return
        
        if len(self.error_history) < 200:
            return
        
        print("\n--- GA-Optimierung läuft ---")
        
        # Einfacher genetischer Algorithmus
        population_groesse = 20
        generationen = 10
        
        # Population initialisieren
        population = []
        for _ in range(population_groesse):
            individuum = {
                'Kp': self.Kp * (0.5 + random.random()),
                'Ki': self.Ki * (0.5 + random.random()),
                'Kd': self.Kd * (0.5 + random.random()),
                'fitness': 0
            }
            population.append(individuum)
        
        # Letzte Fehler für Fitness-Berechnung
        recent_errors = np.array(list(self.error_history)[-200:])
        
        for gen in range(generationen):
            # Fitness berechnen
            for ind in population:
                # Simuliere Performance mit diesen Parametern
                sim_mse = self._simuliere_performance(ind['Kp'], ind['Ki'], ind['Kd'], recent_errors)
                ind['fitness'] = 1.0 / (sim_mse + 1e-6)
            
            # Sortieren
            population.sort(key=lambda x: x['fitness'], reverse=True)
            
            # Beste übernehmen
            neue_population = population[:2]  # Elitismus
            
            while len(neue_population) < population_groesse:
                # Selektion
                elter1 = random.choice(population[:5])
                elter2 = random.choice(population[:5])
                
                # Crossover
                kind = {
                    'Kp': (elter1['Kp'] + elter2['Kp']) / 2,
                    'Ki': (elter1['Ki'] + elter2['Ki']) / 2,
                    'Kd': (elter1['Kd'] + elter2['Kd']) / 2,
                    'fitness': 0
                }
                
                # Mutation
                if random.random() < 0.1:
                    kind['Kp'] *= 0.9 + 0.2 * random.random()
                    kind['Ki'] *= 0.9 + 0.2 * random.random()
                    kind['Kd'] *= 0.9 + 0.2 * random.random()
                
                neue_population.append(kind)
            
            population = neue_population
        
        # Bestes Individuum übernehmen
        bestes = population[0]
        
        # Sanfte Übernahme
        self.Kp = 0.8 * self.Kp + 0.2 * bestes['Kp']
        self.Ki = 0.8 * self.Ki + 0.2 * bestes['Ki']
        self.Kd = 0.8 * self.Kd + 0.2 * bestes['Kd']
        
        print(f"GA-Optimierung: Kp={self.Kp:.3f}, Ki={self.Ki:.3f}, Kd={self.Kd:.3f}")
    
    def _simuliere_performance(self, Kp, Ki, Kd, recent_errors):
        """
        Simuliert die zu erwartende Performance mit gegebenen Parametern
        """
        # Vereinfachte Simulation basierend auf vergangenen Fehlern
        # In der Praxis würde man hier ein Systemmodell verwenden
        
        # Annahme: Bessere Parameter produzieren kleinere zukünftige Fehler
        # Wir verwenden eine gewichtete Kombination
        gewichtung = np.exp(-np.linspace(0, 2, len(recent_errors)))
        gewichtung /= np.sum(gewichtung)
        
        gewichteter_fehler = np.sum(gewichtung * recent_errors**2)
        
        # Parameter-Güte schätzen
        parameterguete = 1.0 / (1 + abs(Kp - self.Kp) + abs(Ki - self.Ki) + abs(Kd - self.Kd))
        
        return gewichteter_fehler * (2 - parameterguete)
    
    def _pt2_reference(self, setpoint):
        """
        PT2-Referenzmodell für MRAC
        """
        # Einfaches PT2 mit gutem Verhalten
        omega = 5.0
        D = 0.7
        
        if not hasattr(self, 'ref_x1'):
            self.ref_x1 = 0
            self.ref_x2 = 0
        
        dt = self.sample_time
        error_ref = setpoint - self.ref_x1
        
        self.ref_x2 += (-2*D*omega*self.ref_x2 - omega**2*self.ref_x1 + omega**2*setpoint) * dt
        self.ref_x1 += self.ref_x2 * dt
        
        return self.ref_x1
    
    def _clamp_parameters(self):
        """
        Begrenzt die PID-Parameter auf sinnvolle Werte
        """
        self.Kp = np.clip(self.Kp, 0.01, 100.0)
        self.Ki = np.clip(self.Ki, 0.0, 50.0)
        self.Kd = np.clip(self.Kd, 0.0, 20.0)
    
    def set_adaptions_parameter(self, **kwargs):
        """
        Setzt Parameter für die Online-Adaption
        
        Args:
            lernrate: Lernrate für Gradientenverfahren
            vergessensfaktor: Für gewichtete Mittelwerte
            adaptions_intervall: Schritte zwischen Adaptionen
        """
        for key, value in kwargs.items():
            if hasattr(self.adapt_params, key):
                setattr(self.adapt_params, key, value)
    
    def set_reference_model(self, model_func):
        """
        Setzt ein Referenzmodell für MRAC
        """
        self.reference_model = model_func
        if self.modus == AdaptionsModus.SELBSTTUNING:
            self.modus = AdaptionsModus.MRAC
    
    def get_current_parameters(self) -> dict:
        """Gibt aktuelle PID-Parameter zurück"""
        return {
            'Kp': self.Kp,
            'Ki': self.Ki,
            'Kd': self.Kd,
            'modus': self.modus.name,
            'adaptions_count': self.adaptions_count
        }
    
    def get_parameter_history(self) -> dict:
        """Gibt die Verläufe aller Parameter zurück"""
        return {
            'Kp': list(self.Kp_history),
            'Ki': list(self.Ki_history),
            'Kd': list(self.Kd_history),
            'time': list(self.time_history)[-len(self.Kp_history):]
        }
    
    def reset(self):
        """Setzt den Regler zurück"""
        self.last_error = 0
        self.integral = 0
        self.last_output = 0
        self.filtered_derivative = 0
        self.derivative_buffer.clear()
        self.error_history.clear()
        self.output_history.clear()
        self.time_history.clear()
        self.Kp_history.clear()
        self.Ki_history.clear()
        self.Kd_history.clear()
        self.setpoint_history.clear()
        self.adaptions_schritt = 0
        
        # Parameter zurücksetzen
        self.Kp = self.Kp_start
        self.Ki = self.Ki_start
        self.Kd = self.Kd_start


# ============================================================================
# BEISPIEL-REGELSTRECKEN
# ============================================================================

class Regelstrecken:
    """Sammlung von Regelstrecken für Tests"""
    
    @staticmethod
    def pt2_system(zustand, stellgroesse, dt):
        """PT2-System (schwingungsfähig)"""
        omega = 2.0
        D = 0.3
        
        if isinstance(zustand, (int, float)):
            x1, x2 = zustand, 0
        else:
            x1, x2 = zustand
        
        dx1 = x2
        dx2 = -2*D*omega*x2 - omega**2*x1 + omega**2*stellgroesse
        
        x1_neu = x1 + dx1 * dt
        x2_neu = x2 + dx2 * dt
        
        return (x1_neu, x2_neu)
    
    @staticmethod
    def zeitvariantes_system(zustand, stellgroesse, dt, t):
        """
        Zeitvariantes System (ändert sich mit der Zeit)
        Ideal zum Testen der Online-Adaption
        """
        omega = 2.0 + 0.5 * np.sin(0.5 * t)  # Zeitvariante Eigenfrequenz
        D = 0.3 + 0.2 * np.sin(0.3 * t)      # Zeitvariante Dämpfung
        
        if isinstance(zustand, (int, float)):
            x1, x2 = zustand, 0
        else:
            x1, x2 = zustand
        
        dx1 = x2
        dx2 = -2*D*omega*x2 - omega**2*x1 + omega**2*stellgroesse
        
        x1_neu = x1 + dx1 * dt
        x2_neu = x2 + dx2 * dt
        
        return (x1_neu, x2_neu)
    
    @staticmethod
    def nichtlinear_system(zustand, stellgroesse, dt):
        """Nichtlineares System mit Sättigung"""
        stellgroesse = np.clip(stellgroesse, -5, 5)
        
        if stellgroesse > 0:
            K = 1.5
        else:
            K = 0.8
        
        return zustand + K * stellgroesse * dt


# ============================================================================
# TEST- UND VISUALISIERUNGSFUNKTIONEN
# ============================================================================

def simuliere_online_adaption(pid, system_func, setpoint_profil, 
                               runtime=30, rauschen=0.01):
    """
    Simuliert die Online-Adaption mit wechselnden Sollwerten
    
    Args:
        pid: OnlineAdaptiverPID-Instanz
        system_func: Systemfunktion
        setpoint_profil: Liste von (zeit, setpoint) Tupeln
        runtime: Simulationsdauer
        rauschen: Messrauschen-Standardabweichung
    
    Returns:
        Dictionary mit Simulationsergebnissen
    """
    dt = pid.sample_time
    t = np.arange(0, runtime, dt)
    
    zustand = 0
    messwerte = []
    setpoints = []
    stellgroessen = []
    Kp_verlauf = []
    Ki_verlauf = []
    Kd_verlauf = []
    fehler_verlauf = []
    
    for i, zeit in enumerate(t):
        # Sollwert aus Profil
        aktueller_setpoint = 0
        for set_zeit, set_wert in setpoint_profil:
            if zeit >= set_zeit:
                aktueller_setpoint = set_wert
        
        pid.setpoint = aktueller_setpoint
        setpoints.append(aktueller_setpoint)
        
        # Messwert mit Rauschen
        if isinstance(zustand, tuple):
            messwert = zustand[0] + np.random.normal(0, rauschen)
        else:
            messwert = zustand + np.random.normal(0, rauschen)
        
        messwerte.append(messwert)
        
        # PID berechnen (mit Zeit für zeitvariante Systeme)
        if system_func == Regelstrecken.zeitvariantes_system:
            stellgroesse = pid.calculate(messwert, zeit)
            zustand = system_func(zustand, stellgroesse, dt, zeit)
        else:
            stellgroesse = pid.calculate(messwert, zeit)
            zustand = system_func(zustand, stellgroesse, dt)
        
        stellgroessen.append(stellgroesse)
        
        # Parameter speichern
        params = pid.get_current_parameters()
        Kp_verlauf.append(params['Kp'])
        Ki_verlauf.append(params['Ki'])
        Kd_verlauf.append(params['Kd'])
        fehler_verlauf.append(aktueller_setpoint - messwert)
    
    return {
        't': t,
        'messwerte': messwerte,
        'setpoints': setpoints,
        'stellgroessen': stellgroessen,
        'Kp_verlauf': Kp_verlauf,
        'Ki_verlauf': Ki_verlauf,
        'Kd_verlauf': Kd_verlauf,
        'fehler': fehler_verlauf
    }


def plotte_ergebnisse(ergebnisse, titel="Online-Adaptive PID-Regelung"):
    """
    Visualisiert die Simulationsergebnisse
    """
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    
    t = ergebnisse['t']
    
    # Regelgröße
    ax1 = axes[0, 0]
    ax1.plot(t, ergebnisse['messwerte'], 'b-', label='Istwert', linewidth=1)
    ax1.plot(t, ergebnisse['setpoints'], 'r--', label='Sollwert', linewidth=2)
    ax1.set_ylabel('Regelgröße')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_title(titel)
    
    # Stellgröße
    ax2 = axes[0, 1]
    ax2.plot(t, ergebnisse['stellgroessen'], 'g-', label='Stellgröße', linewidth=1)
    ax2.set_ylabel('Stellgröße')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_title('Stellsignal')
    
    # Kp-Verlauf
    ax3 = axes[1, 0]
    ax3.plot(t, ergebnisse['Kp_verlauf'], 'm-', label='Kp', linewidth=2)
    ax3.set_ylabel('Kp')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    ax3.set_title('Proportionalverstärkung (online adaptiert)')
    
    # Ki-Verlauf
    ax4 = axes[1, 1]
    ax4.plot(t, ergebnisse['Ki_verlauf'], 'c-', label='Ki', linewidth=2)
    ax4.set_ylabel('Ki')
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    ax4.set_title('Integralverstärkung (online adaptiert)')
    
    # Kd-Verlauf
    ax5 = axes[2, 0]
    ax5.plot(t, ergebnisse['Kd_verlauf'], 'y-', label='Kd', linewidth=2)
    ax5.set_xlabel('Zeit (s)')
    ax5.set_ylabel('Kd')
    ax5.legend()
    ax5.grid(True, alpha=0.3)
    ax5.set_title('Differenzialverstärkung (online adaptiert)')
    
    # Fehler
    ax6 = axes[2, 1]
    ax6.plot(t, ergebnisse['fehler'], 'r-', label='Regelfehler', linewidth=1)
    ax6.set_xlabel('Zeit (s)')
    ax6.set_ylabel('Fehler')
    ax6.legend()
    ax6.grid(True, alpha=0.3)
    ax6.set_title('Regelfehler')
    
    plt.tight_layout()
    plt.show()


def berechne_metriken(ergebnisse):
    """Berechnet Performance-Metriken"""
    fehler = np.array(ergebnisse['fehler'])
    
    mse = np.mean(fehler**2)
    mae = np.mean(np.abs(fehler))
    max_fehler = np.max(np.abs(fehler))
    
    # Überschwingen (maximaler positiver Fehler nach Sollwertsprung)
    ueberschwingen = []
    letzter_setpunkt = ergebnisse['setpoints'][0]
    for i, sp in enumerate(ergebnisse['setpoints']):
        if sp != letzter_setpunkt:
            # Nach Sollwertänderung
            ausschnitt = fehler[max(0, i-50):min(len(fehler), i+100)]
            if len(ausschnitt) > 0:
                ueberschwingen.append(np.max(ausschnitt))
            letzter_setpunkt = sp
    
    return {
        'MSE': mse,
        'MAE': mae,
        'Max Fehler': max_fehler,
        'Überschwingen (Ø)': np.mean(ueberschwingen) if ueberschwingen else 0
    }


# ============================================================================
# HAUPTBEISPIEL UND VERGLEICH
# ============================================================================

def beispiel_zeitvariantes_system():
    """
    Beispiel: Online-Adaption für zeitvariantes System
    """
    print("\n" + "="*60)
    print("BEISPIEL 1: ZEITVARIANTES SYSTEM")
    print("="*60)
    
    # Sollwertprofil
    profil = [
        (0, 0),
        (2, 10),
        (8, 5),
        (14, 15),
        (20, 0),
        (25, 8)
    ]
    
    # Verschiedene Adaptionsmodi vergleichen
    modi = [
        (AdaptionsModus.SELBSTTUNING, "Selbsttuning"),
        (AdaptionsModus.GRADIENT, "Gradient"),
        (AdaptionsModus.HYBRID, "Hybrid")
    ]
    
    ergebnisse = {}
    
    for modus, name in modi:
        print(f"\nTeste {name}...")
        
        pid = OnlineAdaptiverPID(
            Kp_start=1.0,
            Ki_start=0.2,
            Kd_start=0.05,
            setpoint=0,
            sample_time=0.01,
            modus=modus
        )
        
        pid.set_adaptions_parameter(
            lernrate=0.02,
            adaptions_intervall=5
        )
        
        ergebnis = simuliere_online_adaption(
            pid,
            Regelstrecken.zeitvariantes_system,
            profil,
            runtime=30,
            rauschen=0.05
        )
        
        ergebnisse[name] = ergebnis
        
        metriken = berechne_metriken(ergebnis)
        print(f"  MSE: {metriken['MSE']:.4f}")
        print(f"  MAE: {metriken['MAE']:.4f}")
    
    # Beste Ergebnisse plotten
    best_name = min(ergebnisse.keys(), 
                   key=lambda x: berechne_metriken(ergebnisse[x])['MSE'])
    
    plotte_ergebnisse(ergebnisse[best_name], 
                     f"Online-Adaption ({best_name}) für zeitvariantes System")
    
    return ergebnisse


def beispiel_nichtlinear_mit_stoerung():
    """
    Beispiel: Nichtlineares System mit Störungen
    """
    print("\n" + "="*60)
    print("BEISPIEL 2: NICHTLINEARES SYSTEM MIT STÖRUNGEN")
    print("="*60)
    
    profil = [(0, 0), (1, 10), (4, 5), (7, 12), (10, 0)]
    
    # Mit Online-Adaption
    pid_adaptiv = OnlineAdaptiverPID(
        Kp_start=0.8,
        Ki_start=0.15,
        Kd_start=0.03,
        sample_time=0.01,
        modus=AdaptionsModus.HYBRID
    )
    
    ergebnis_adaptiv = simuliere_online_adaption(
        pid_adaptiv,
        Regelstrecken.nichtlinear_system,
        profil,
        runtime=15,
        rauschen=0.02
    )
    
    # Ohne Adaption (feste Parameter)
    pid_fest = OnlineAdaptiverPID(
        Kp_start=0.8,
        Ki_start=0.15,
        Kd_start=0.03,
        sample_time=0.01,
        modus=AdaptionsModus.SELBSTTUNING  # deaktiviert durch setzen von lernrate=0
    )
    pid_fest.set_adaptions_parameter(lernrate=0)  # Keine Adaption
    
    ergebnis_fest = simuliere_online_adaption(
        pid_fest,
        Regelstrecken.nichtlinear_system,
        profil,
        runtime=15,
        rauschen=0.02
    )
    
    # Vergleich plotten
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    t = ergebnis_adaptiv['t']
    
    ax1.plot(t, ergebnis_adaptiv['messwerte'], 'b-', label='Adaptiv', linewidth=1)
    ax1.plot(t, ergebnis_fest['messwerte'], 'g-', label='Fest', linewidth=1)
    ax1.plot(t, ergebnis_adaptiv['setpoints'], 'r--', label='Sollwert', linewidth=2)
    ax1.set_ylabel('Regelgröße')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_title('Vergleich: Adaptive vs. feste Parameter')
    
    # Fehler
    fehler_adaptiv = np.array(ergebnis_adaptiv['fehler'])
    fehler_fest = np.array(ergebnis_fest['fehler'])
    
    ax2.plot(t, fehler_adaptiv, 'b-', label='Adaptiv Fehler', alpha=0.7)
    ax2.plot(t, fehler_fest, 'g-', label='Fest Fehler', alpha=0.7)
    ax2.set_xlabel('Zeit (s)')
    ax2.set_ylabel('Regelfehler')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()
    
    metriken_adaptiv = berechne_metriken(ergebnis_adaptiv)
    metriken_fest = berechne_metriken(ergebnis_fest)
    
    print("\nPerformance-Vergleich:")
    print(f"Adaptiv - MSE: {metriken_adaptiv['MSE']:.4f}")
    print(f"Fest    - MSE: {metriken_fest['MSE']:.4f}")
    print(f"Verbesserung: {(metriken_fest['MSE'] - metriken_adaptiv['MSE'])/metriken_fest['MSE']*100:.1f}%")
    
    return pid_adaptiv.get_parameter_history()


def beispiel_mrac():
    """
    Beispiel: Model Reference Adaptive Control (MRAC)
    """
    print("\n" + "="*60)
    print("BEISPIEL 3: MRAC (MODEL REFERENCE ADAPTIVE CONTROL)")
    print("="*60)
    
    profil = [(0, 0), (1, 10), (4, 5), (7, 15), (10, 0)]
    
    pid_mrac = OnlineAdaptiverPID(
        Kp_start=0.5,
        Ki_start=0.1,
        Kd_start=0.02,
        sample_time=0.01,
        modus=AdaptionsModus.MRAC
    )
    
    # Referenzmodell ist bereits in der Klasse definiert
    
    ergebnis = simuliere_online_adaption(
        pid_mrac,
        Regelstrecken.pt2_system,
        profil,
        runtime=15,
        rauschen=0.01
    )
    
    plotte_ergebnisse(ergebnis, "MRAC Online-Adaption")
    
    return ergebnis


def online_adaption_demo():
    """
    Haupt-Demo mit interaktiver Auswahl
    """
    print("\n" + "="*60)
    print("ONLINE-ADAPTIVE PID-REGELUNG - DEMO")
    print("="*60)
    
    while True:
        print("\nVerfügbare Beispiele:")
        print("1. Zeitvariantes System")
        print("2. Nichtlineares System mit Störungen")
        print("3. MRAC (Model Reference)")
        print("4. Alle Beispiele")
        print("0. Beenden")
        
        choice = input("\nAuswahl (0-4): ").strip()
        
        if choice == '1':
            beispiel_zeitvariantes_system()
        elif choice == '2':
            beispiel_nichtlinear_mit_stoerung()
        elif choice == '3':
            beispiel_mrac()
        elif choice == '4':
            beispiel_zeitvariantes_system()
            beispiel_nichtlinear_mit_stoerung()
            beispiel_mrac()
        elif choice == '0':
            break
        else:
            print("Ungültige Auswahl!")


# ============================================================================
# EINFACHES PRAXISBEISPIEL
# ============================================================================

def einfaches_praxisbeispiel():
        
    # PID mit Online-Adaption erstellen
    pid = OnlineAdaptiverPID(
        Kp_start=1.0,
        Ki_start=0.02,
        Kd_start=0.005,
        setpoint=10,
        sample_time=0.01,
        modus=AdaptionsModus.HYBRID
    )
    
    # Adaptionsparameter anpassen
    pid.set_adaptions_parameter(
        lernrate=0.02,
        adaptions_intervall=5
    )
    
    # Simulation
    dt = pid.sample_time
    t = np.arange(0, 20, dt)
    
    zustand = 0
    messwerte = []
    setpoints = []
    
    print("\nStarte Simulation...")
    print("Zeit | Messwert | Sollwert | Kp    | Ki    | Kd")
    print("-" * 50)
    
    for i, zeit in enumerate(t):
        # Sollwert ändern
        if zeit < 3:
            pid.setpoint = 5
        elif zeit < 7:
            pid.setpoint = 12
        elif zeit < 12:
            pid.setpoint = 3
        elif zeit < 16:
            pid.setpoint = 8
        else:
            pid.setpoint = 5
        
        setpoints.append(pid.setpoint)
        
        # PID berechnen
        stellgroesse = pid.calculate(zustand, zeit)
        
        # System simulieren (PT2)
        zustand = Regelstrecken.pt2_system(zustand, stellgroesse, dt)
        
        if isinstance(zustand, tuple):
            messwert = zustand[0]
        else:
            messwert = zustand
        
        messwerte.append(messwert)
        
        # Alle 50 Schritte ausgeben
        if i % 50 == 0:
            params = pid.get_current_parameters()
            print(f"{zeit:4.1f} | {messwert:7.2f} | {pid.setpoint:7.2f} | "
                  f"{params['Kp']:5.3f} | {params['Ki']:5.3f} | {params['Kd']:5.3f}")
    
    print("-" * 50)
    print("Simulation beendet")
    print(f"Finale Parameter: {pid.get_current_parameters()}")
    
    # Plot
    plt.figure(figsize=(12, 8))
    
    plt.subplot(2, 1, 1)
    plt.plot(t, messwerte, 'b-', label='Istwert', linewidth=1)
    plt.plot(t, setpoints, 'r--', label='Sollwert', linewidth=2)
    plt.ylabel('Regelgröße')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.title('Online-Adaptive PID-Regelung - Einfaches Beispiel')
    
    plt.subplot(2, 1, 2)
    history = pid.get_parameter_history()
    if history['Kp']:
        plt.plot(t[:len(history['Kp'])], history['Kp'], 'm-', label='Kp', linewidth=2)
        plt.plot(t[:len(history['Ki'])], history['Ki'], 'c-', label='Ki', linewidth=2)
        plt.plot(t[:len(history['Kd'])], history['Kd'], 'y-', label='Kd', linewidth=2)
        plt.xlabel('Zeit (s)')
        plt.ylabel('Parameter')
        plt.legend()
        plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()


# ============================================================================
# HAUPTFUNKTION
# ============================================================================

if __name__ == "__main__":
    
    import random  # Für GA-Beispiel
       
    # Einfaches Beispiel direkt ausführen
    einfaches_praxisbeispiel()
    
    #online_adaption_demo()