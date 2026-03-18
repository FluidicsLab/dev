"""
Genetischer Algorithmus zur PID-Regler Optimierung
==================================================
Optimiert automatisch die PID-Parameter (Kp, Ki, Kd) für gegebene Regelstrecken.
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import List, Tuple, Callable, Optional
import random
import time
from collections import deque

# ============================================================================
# KERNKOMPONENTEN DES GENETISCHEN ALGORITHMUS
# ============================================================================

@dataclass
class PIDIndividuum:
    """Ein Individuum = Ein Satz PID-Parameter"""
    Kp: float
    Ki: float
    Kd: float
    fitness: float = 0.0
    generation: int = 0
    
    def __str__(self):
        return f"Kp={self.Kp:.4f}, Ki={self.Ki:.4f}, Kd={self.Kd:.4f} (Fitness={self.fitness:.6f})"
    
    def als_tuple(self) -> Tuple[float, float, float]:
        return (self.Kp, self.Ki, self.Kd)


class GenetischerAlgorithmus:
    """
    Genetischer Algorithmus zur PID-Optimierung
    
    Features:
    - Turnier-Selektion
    - BLX-α Crossover
    - Gauß-Mutation
    - Elitismus
    - Fitness-Sharing (optional)
    """
    
    def __init__(self, 
                 population_groesse: int = 50,
                 mutation_rate: float = 0.1,
                 crossover_rate: float = 0.8,
                 elitismus_anteil: float = 0.1,
                 turnier_groesse: int = 3,
                 param_grenzen: dict = None):
        """
        Initialisiert den genetischen Algorithmus
        
        Args:
            population_groesse: Anzahl Individuen pro Generation
            mutation_rate: Wahrscheinlichkeit für Mutation (0-1)
            crossover_rate: Wahrscheinlichkeit für Crossover (0-1)
            elitismus_anteil: Anteil der besten Individuen, die überleben
            turnier_groesse: Größe des Turniers für Selektion
            param_grenzen: Dictionary mit (min, max) für ['Kp', 'Ki', 'Kd']
        """
        self.population_groesse = population_groesse
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitismus_anzahl = max(1, int(population_groesse * elitismus_anteil))
        self.turnier_groesse = turnier_groesse
        
        # Standard-Parametergrenzen
        self.param_grenzen = param_grenzen or {
            'Kp': (0.0, 10.0),
            'Ki': (0.0, 5.0),
            'Kd': (0.0, 2.0)
        }
        
        # Populationsvariablen
        self.population: List[PIDIndividuum] = []
        self.bestes_individuum: Optional[PIDIndividuum] = None
        self.generation = 0
        
        # Statistik
        self.fitness_verlauf: List[float] = []
        self.durchschnitt_fitness_verlauf: List[float] = []
        
    def initialisiere_population(self, start_individuum: Optional[PIDIndividuum] = None):
        """
        Erzeugt die Startpopulation
        
        Args:
            start_individuum: Optional Startwert (z.B. manuelle Einstellung)
        """
        self.population = []
        
        # Startindividuum hinzufügen falls vorhanden
        if start_individuum:
            self.population.append(start_individuum)
        
        # Rest mit zufälligen Individuen füllen
        while len(self.population) < self.population_groesse:
            individuum = PIDIndividuum(
                Kp=random.uniform(*self.param_grenzen['Kp']),
                Ki=random.uniform(*self.param_grenzen['Ki']),
                Kd=random.uniform(*self.param_grenzen['Kd'])
            )
            self.population.append(individuum)
    
    def berechne_fitness(self, 
                        individuum: PIDIndividuum, 
                        fitness_func: Callable[[float, float, float], float]) -> float:
        """
        Berechnet die Fitness eines Individuums
        
        Args:
            individuum: Das zu bewertende Individuum
            fitness_func: Funktion, die (Kp, Ki, Kd) annimmt und Fitness zurückgibt
                         (Höhere Fitness = besser)
        """
        individuum.fitness = fitness_func(individuum.Kp, individuum.Ki, individuum.Kd)
        return individuum.fitness
    
    def bewerte_population(self, fitness_func: Callable[[float, float, float], float]):
        """Bewertet alle Individuen der Population"""
        for individuum in self.population:
            self.berechne_fitness(individuum, fitness_func)
    
    def turnier_selektion(self) -> PIDIndividuum:
        """
        Turnierauswahl: Wählt das beste aus einer zufälligen Gruppe
        
        Returns:
            Ausgewähltes Individuum
        """
        turnier = random.sample(self.population, self.turnier_groesse)
        return max(turnier, key=lambda ind: ind.fitness)
    
    def crossover(self, 
                  elter1: PIDIndividuum, 
                  elter2: PIDIndividuum) -> Tuple[PIDIndividuum, PIDIndividuum]:
        """
        BLX-α Crossover (Blend Crossover)
        Erzeugt Kinder durch Interpolation der Eltern
        """
        if random.random() > self.crossover_rate:
            # Kein Crossover: Eltern kopieren
            return (PIDIndividuum(elter1.Kp, elter1.Ki, elter1.Kd),
                   PIDIndividuum(elter2.Kp, elter2.Ki, elter2.Kd))
        
        alpha = 0.5  # Blend-Faktor
        
        kind1 = PIDIndividuum(0, 0, 0)
        kind2 = PIDIndividuum(0, 0, 0)
        
        for param in ['Kp', 'Ki', 'Kd']:
            wert1 = getattr(elter1, param)
            wert2 = getattr(elter2, param)
            
            min_wert = min(wert1, wert2)
            max_wert = max(wert1, wert2)
            intervall = max_wert - min_wert
            
            # Erweitertes Intervall für bessere Exploration
            unten = min_wert - alpha * intervall
            oben = max_wert + alpha * intervall
            
            # Kinder im erweiterten Intervall erzeugen
            kind_wert1 = random.uniform(unten, oben)
            kind_wert2 = random.uniform(unten, oben)
            
            # Parameter in Grenzen halten
            grenzen = self.param_grenzen[param]
            setattr(kind1, param, np.clip(kind_wert1, grenzen[0], grenzen[1]))
            setattr(kind2, param, np.clip(kind_wert2, grenzen[0], grenzen[1]))
        
        kind1.generation = self.generation + 1
        kind2.generation = self.generation + 1
        
        return kind1, kind2
    
    def mutiere(self, individuum: PIDIndividuum) -> PIDIndividuum:
        """
        Gauß-Mutation mit adaptiver Schrittweite
        """
        for param in ['Kp', 'Ki', 'Kd']:
            if random.random() < self.mutation_rate:
                aktuell = getattr(individuum, param)
                grenzen = self.param_grenzen[param]
                
                # Standardabweichung = 10% des Wertebereichs
                sigma = (grenzen[1] - grenzen[0]) * 0.1
                
                # Gauß-Mutation
                neu = aktuell + random.gauss(0, sigma)
                
                # In Grenzen halten
                setattr(individuum, param, np.clip(neu, grenzen[0], grenzen[1]))
        
        return individuum
    
    def evolviere(self, fitness_func: Callable[[float, float, float], float]) -> PIDIndividuum:
        """
        Erzeugt die nächste Generation
        
        Args:
            fitness_func: Funktion zur Fitnessberechnung
            
        Returns:
            Bestes Individuum der neuen Generation
        """
        # Fitness berechnen
        self.bewerte_population(fitness_func)
        
        # Nach Fitness sortieren
        self.population.sort(key=lambda ind: ind.fitness, reverse=True)
        
        # Bestes Individuum speichern
        aktuell_bestes = self.population[0]
        if (self.bestes_individuum is None or 
            aktuell_bestes.fitness > self.bestes_individuum.fitness):
            self.bestes_individuum = PIDIndividuum(
                aktuell_bestes.Kp, aktuell_bestes.Ki, aktuell_bestes.Kd,
                aktuell_bestes.fitness
            )
        
        # Statistik aktualisieren
        self.fitness_verlauf.append(self.bestes_individuum.fitness)
        durchschnitt = np.mean([ind.fitness for ind in self.population])
        self.durchschnitt_fitness_verlauf.append(durchschnitt)
        
        # Elitismus: Beste Individuen direkt übernehmen
        neue_population = []
        for i in range(self.elitismus_anzahl):
            elite = PIDIndividuum(
                self.population[i].Kp,
                self.population[i].Ki,
                self.population[i].Kd,
                self.population[i].fitness,
                self.generation + 1
            )
            neue_population.append(elite)
        
        # Rest durch Selektion, Crossover und Mutation erzeugen
        while len(neue_population) < self.population_groesse:
            # Eltern auswählen
            elter1 = self.turnier_selektion()
            elter2 = self.turnier_selektion()
            
            # Crossover
            kind1, kind2 = self.crossover(elter1, elter2)
            
            # Mutation
            kind1 = self.mutiere(kind1)
            kind2 = self.mutiere(kind2)
            
            neue_population.append(kind1)
            if len(neue_population) < self.population_groesse:
                neue_population.append(kind2)
        
        self.population = neue_population
        self.generation += 1
        
        return self.bestes_individuum
    
    def plot_fitness_verlauf(self):
        """Visualisiert den Fitness-Verlauf über die Generationen"""
        if not self.fitness_verlauf:
            print("Keine Daten zum Plotten vorhanden")
            return
        
        plt.figure(figsize=(10, 6))
        generationen = range(1, len(self.fitness_verlauf) + 1)
        
        plt.plot(generationen, self.fitness_verlauf, 'b-', label='Beste Fitness', linewidth=2)
        plt.plot(generationen, self.durchschnitt_fitness_verlauf, 'r--', 
                label='Durchschnittliche Fitness', linewidth=2)
        
        plt.xlabel('Generation')
        plt.ylabel('Fitness')
        plt.title('Fitness-Verlauf des Genetischen Algorithmus')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.show()


# ============================================================================
# PID-REGLER FÜR SIMULATION
# ============================================================================

class PIDRegler:
    """Einfacher PID-Regler für Simulationszwecke"""
    
    def __init__(self, Kp: float, Ki: float, Kd: float, setpoint: float = 0):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        
        self.last_error = 0
        self.integral = 0
        
    def berechnen(self, messwert: float, dt: float) -> float:
        
        error = self.setpoint - (messwert if isinstance(messwert, (int, float)) else messwert[0])
        
        self.integral += error * dt
        derivative = (error - self.last_error) / dt if dt > 0 else 0
        
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        
        self.last_error = error
        return output
    
    def reset(self):
        self.last_error = 0
        self.integral = 0


# ============================================================================
# FITNESS-FUNKTIONEN
# ============================================================================

class FitnessFunctionen:
    """Sammlung verschiedener Fitness-Funktionen für PID-Optimierung"""
    
    @staticmethod
    def mse_gewichtete_fitness(Kp: float, Ki: float, Kd: float,
                               system_func: Callable,
                               setpunkt_profil: List[Tuple[float, float]],
                               sample_time: float = 0.01,
                               rauschen: float = 0.0) -> float:
        """
        Fitness basierend auf MSE (Mean Squared Error)
        Je kleiner der Fehler, desto höher die Fitness
        """
        dt = sample_time
        sim_dauer = setpunkt_profil[-1][0] + 2  # Letzte Zeit + 2 Sekunden
        t = np.arange(0, sim_dauer, dt)
        
        zustand = 0
        fehler_liste = []
        aktueller_setpunkt = 0
        
        for zeit in t:
            # Aktuellen Sollwert aus Profil
            for set_zeit, set_wert in setpunkt_profil:
                if zeit >= set_zeit:
                    aktueller_setpunkt = set_wert
            
            # PID berechnen
            error = aktueller_setpunkt - zustand
            fehler_liste.append(error)
            
            # PID-Parameter (vereinfacht für Fitness-Berechnung)
            pid = PIDRegler(Kp, Ki, Kd, aktueller_setpunkt)
            stellgroesse = pid.berechnen(zustand, dt)
            
            # System simulieren
            zustand = system_func(zustand, stellgroesse, dt)
        
        # MSE berechnen
        fehler_array = np.array(fehler_liste)
        mse = np.mean(fehler_array**2)
        
        # Fitness = 1 / (1 + MSE) -> [0, 1], höher = besser
        fitness = 1.0 / (1.0 + mse)
        
        return fitness
    
    @staticmethod
    def multi_kriterium_fitness(Kp: float, Ki: float, Kd: float,
                               system_func: Callable,
                               setpunkt_profil: List[Tuple[float, float]],
                               sample_time: float = 0.01) -> float:
        """
        Fitness mit mehreren Kriterien:
        - MSE (Genauigkeit)
        - Überschwingen
        - Einschwingzeit
        """
        dt = sample_time
        sim_dauer = setpunkt_profil[-1][0] + 2
        t = np.arange(0, sim_dauer, dt)
        
        zustand = 0
        fehler_liste = []
        stellgroessen = []
        aktueller_setpunkt = 0
        setpunkt_liste = []
        
        for zeit in t:
            for set_zeit, set_wert in setpunkt_profil:
                if zeit >= set_zeit:
                    aktueller_setpunkt = set_wert
            
            setpunkt_liste.append(aktueller_setpunkt)
            
            error = aktueller_setpunkt - zustand if isinstance(zustand, (int, float)) else zustand[0]

            fehler_liste.append(error)
            
            pid = PIDRegler(Kp, Ki, Kd, aktueller_setpunkt)
            stellgroesse = pid.berechnen(zustand, dt)
            stellgroessen.append(stellgroesse)
            
            zustand = system_func(zustand, stellgroesse, dt)
        
        fehler_array = np.array(fehler_liste)
        
        # 1. MSE (Genauigkeit)
        mse = np.mean(fehler_array**2)
        
        # 2. Überschwingen (maximaler positiver Fehler)
        ueberschwingen = np.max(fehler_array) if np.max(fehler_array) > 0 else 0
        
        # 3. Einschwingzeit (wann bleibt Fehler unter 2%)
        einschwingzeit = len(fehler_array)
        toleranz = 0.02 * np.max(np.abs(setpunkt_liste)) if np.max(setpunkt_liste) != 0 else 0.1
        for i in range(len(fehler_array)-1, 0, -1):
            if abs(fehler_array[i]) > toleranz:
                einschwingzeit = i
                break
        
        # 4. Stellgrößenänderung (Verschleiß)
        stell_diff = np.diff(stellgroessen)
        stell_aktivitaet = np.mean(np.abs(stell_diff))
        
        # Gewichtete Summe (niedriger = besser)
        gesamt_fehler = (1.0 * mse + 
                        0.5 * ueberschwingen + 
                        0.01 * einschwingzeit + 
                        0.1 * stell_aktivitaet)
        
        # Fitness (höher = besser)
        fitness = 1.0 / (gesamt_fehler + 1e-6)
        
        return fitness


# ============================================================================
# BEISPIEL-REGELSTRECKEN
# ============================================================================

class BeispielSysteme:
    """Sammlung von Beispiel-Regelstrecken für Tests"""
    
    @staticmethod
    def pt1_system(zustand, stellgroesse, dt):
        """PT1-Glied (Verzögerung 1. Ordnung)"""
        T = 0.5  # Zeitkonstante
        K = 1.0  # Verstärkung
        return zustand + (K * stellgroesse - zustand) * dt / T
    
    @staticmethod
    def pt2_system(zustand, stellgroesse, dt):
        """PT2-Glied (schwingungsfähig)"""
        omega = 2.0  # Eigenfrequenz
        D = 0.3      # Dämpfung
        
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
        # Sättigung
        stellgroesse = np.clip(stellgroesse, -5, 5)
        
        # Nichtlineare Kennlinie
        if stellgroesse > 0:
            return zustand + stellgroesse * dt * 1.5
        else:
            return zustand + stellgroesse * dt * 0.8
    
    @staticmethod
    def totzeit_system(zustand, stellgroesse, dt):
        """System mit Totzeit (vereinfacht)"""
        # Einfache Totzeit-Simulation
        if not hasattr(totzeit_system, "puffer"):
            totzeit_system.puffer = deque(maxlen=int(0.5 / dt))  # 0.5s Totzeit
            for _ in range(totzeit_system.puffer.maxlen):
                totzeit_system.puffer.append(0)
        
        totzeit_system.puffer.append(stellgroesse)
        wirksame_stellgroesse = totzeit_system.puffer[0]
        
        # PT1-Verhalten
        T = 0.3
        return zustand + (wirksame_stellgroesse - zustand) * dt / T


# ============================================================================
# OPTIMIERER FÜR PID-REGLER
# ============================================================================

class PIDOptimierer:
    """
    Hauptklasse zur PID-Optimierung mit genetischem Algorithmus
    """
    
    def __init__(self, 
                 system_func: Callable,
                 sample_time: float = 0.01,
                 ga_parameter: dict = None):
        """
        Args:
            system_func: Funktion der Regelstrecke (zustand, stellgroesse, dt) -> neuer_zustand
            sample_time: Abtastzeit für Simulation
            ga_parameter: Parameter für den genetischen Algorithmus
        """
        self.system_func = system_func
        self.sample_time = sample_time
        
        # GA initialisieren
        self.ga = GenetischerAlgorithmus(**(ga_parameter or {}))
        
        # Test-Szenario für Fitness-Berechnung
        self.test_profil = [
            (0, 0),
            (1, 10),
            (5, 5),
            (9, 15),
            (13, 0)
        ]
        
    def fitness_func(self, Kp: float, Ki: float, Kd: float) -> float:
        """
        Fitness-Funktion für die Optimierung
        Kann durch verschiedene Strategien ersetzt werden
        """
        return FitnessFunctionen.multi_kriterium_fitness(
            Kp, Ki, Kd,
            self.system_func,
            self.test_profil,
            self.sample_time
        )
    
    def optimiere(self, 
                  generationen: int = 50,
                  start_params: Optional[Tuple[float, float, float]] = None) -> PIDIndividuum:
        """
        Führt die Optimierung durch
        
        Args:
            generationen: Anzahl der Generationen
            start_params: Optionale Startparameter (Kp, Ki, Kd)
            
        Returns:
            Optimales Individuum
        """
        print("\n" + "="*60)
        print("PID-OPTIMIERUNG MIT GENETISCHEM ALGORITHMUS")
        print("="*60)
        
        # Startpopulation initialisieren
        start_individuum = None
        if start_params:
            start_individuum = PIDIndividuum(*start_params)
        
        self.ga.initialisiere_population(start_individuum)
        
        print(f"Population: {self.ga.population_groesse} Individuen")
        print(f"Generationen: {generationen}")
        print(f"Mutationsrate: {self.ga.mutation_rate}")
        print(f"Crossoverrate: {self.ga.crossover_rate}")
        print("-" * 60)
        
        start_zeit = time.time()
        
        for gen in range(generationen):
            bestes = self.ga.evolviere(self.fitness_func)
            
            if (gen + 1) % 10 == 0 or gen == 0:
                print(f"Generation {gen+1:2d}: Beste Fitness = {bestes.fitness:.6f} | "
                      f"Kp={bestes.Kp:.3f}, Ki={bestes.Ki:.3f}, Kd={bestes.Kd:.3f}")
        
        end_zeit = time.time()
        
        print("-" * 60)
        print(f"Optimierung abgeschlossen in {end_zeit - start_zeit:.2f}s")
        print(f"Beste gefundene Parameter: {self.ga.bestes_individuum}")
        
        return self.ga.bestes_individuum
    
    def visualisiere_ergebnis(self, individuum: PIDIndividuum):
        """
        Visualisiert das Optimierungsergebnis
        """
        # Simulation mit optimierten Parametern
        dt = self.sample_time
        sim_dauer = self.test_profil[-1][0] + 2
        t = np.arange(0, sim_dauer, dt)
        
        zustand = 0
        messwerte = []
        setpunkte = []
        stellgroessen = []
        
        for zeit in t:
            # Aktuellen Sollwert
            aktueller_setpunkt = 0
            for set_zeit, set_wert in self.test_profil:
                if zeit >= set_zeit:
                    aktueller_setpunkt = set_wert
            
            setpunkte.append(aktueller_setpunkt)
            
            # PID
            pid = PIDRegler(individuum.Kp, individuum.Ki, individuum.Kd, aktueller_setpunkt)
            stellgroesse = pid.berechnen(zustand, dt)
            stellgroessen.append(stellgroesse)
            
            # System
            zustand = self.system_func(zustand, stellgroesse, dt)
            
            if isinstance(zustand, tuple):
                messwerte.append(zustand[0])
            else:
                messwerte.append(zustand)
        
        # Plot
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
        
        ax1.plot(t, messwerte, 'b-', label='Istwert', linewidth=1)
        ax1.plot(t, setpunkte, 'r--', label='Sollwert', linewidth=2)
        ax1.set_ylabel('Regelgröße')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_title(f'Optimierte PID-Parameter: Kp={individuum.Kp:.3f}, '
                     f'Ki={individuum.Ki:.3f}, Kd={individuum.Kd:.3f}')
        
        ax2.plot(t, stellgroessen, 'g-', label='Stellgröße', linewidth=1)
        ax2.set_ylabel('Stellgröße')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        # Fehler
        fehler = np.array(setpunkte) - np.array(messwerte)
        ax3.plot(t, fehler, 'm-', label='Regelfehler', linewidth=1)
        ax3.set_xlabel('Zeit (s)')
        ax3.set_ylabel('Fehler')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
        
        # Fitness-Verlauf plotten
        self.ga.plot_fitness_verlauf()


# ============================================================================
# HAUPTPROGRAMM UND BEISPIELE
# ============================================================================

def beispiel_pt2_optimierung():

    optimierer = PIDOptimierer(
        system_func=BeispielSysteme.pt2_system,
        sample_time=0.01,
        ga_parameter={
            'population_groesse': 50,
            'mutation_rate': 0.15,
            'crossover_rate': 0.8,
            'param_grenzen': {
                'Kp': (0.0, 5.0),
                'Ki': (0.0, 2.0),
                'Kd': (0.0, 1.0)
            }
        }
    )
    
    bestes = optimierer.optimiere(generationen=40)
    optimierer.visualisiere_ergebnis(bestes)
    
    return bestes


def beispiel_nichtlinear_optimierung():
    
    optimierer = PIDOptimierer(
        system_func=BeispielSysteme.nichtlinear_system,
        sample_time=0.01,
        ga_parameter={
            'population_groesse': 60,
            'mutation_rate': 0.2,
            'crossover_rate': 0.85,
            'param_grenzen': {
                'Kp': (0.0, 8.0),
                'Ki': (0.0, 3.0),
                'Kd': (0.0, 1.5)
            }
        }
    )
    
    bestes = optimierer.optimiere(generationen=50)
    optimierer.visualisiere_ergebnis(bestes)
    
    return bestes


def beispiel_totzeit_optimierung():
    
    # Totzeit-System erfordert andere Parameter-Grenzen
    optimierer = PIDOptimierer(
        system_func=BeispielSysteme.totzeit_system,
        sample_time=0.01,
        ga_parameter={
            'population_groesse': 70,
            'mutation_rate': 0.1,
            'crossover_rate': 0.75,
            'param_grenzen': {
                'Kp': (0.0, 3.0),
                'Ki': (0.0, 1.0),
                'Kd': (0.0, 0.8)
            }
        }
    )
    
    bestes = optimierer.optimiere(generationen=60)
    optimierer.visualisiere_ergebnis(bestes)
    
    return bestes


def vergleich_mit_ziegler_nichols():
    """
    Vergleich: GA-Optimierung vs. Ziegler-Nichols
    """
    print("\n" + "="*60)
    print("VERGLEICH: GA VS. ZIEGLER-NICHOLS")
    print("="*60)
    
    # PT2-System
    system = BeispielSysteme.pt2_system
    
    # GA-Optimierung
    optimierer = PIDOptimierer(
        system_func=system,
        sample_time=0.01,
        ga_parameter={
            'population_groesse': 40,
            'mutation_rate': 0.1,
            'param_grenzen': {
                'Kp': (0.0, 6.0),
                'Ki': (0.0, 3.0),
                'Kd': (0.0, 1.5)
            }
        }
    )
    
    ga_params = optimierer.optimiere(generationen=30)
    
    # Ziegler-Nichols (angenähert für PT2)
    # Ku ≈ 4, Tu ≈ 1.5 (geschätzt für dieses System)
    Ku, Tu = 4.0, 1.5
    zn_params = PIDIndividuum(
        Kp=0.6 * Ku,
        Ki=1.2 * Ku / Tu,
        Kd=0.075 * Ku * Tu
    )
    
    print(f"\nZiegler-Nichols: {zn_params}")
    print(f"GA-Optimierung:   {ga_params}")
    
    # Simulation mit beiden Parametern
    dt = 0.01
    profil = [(0, 0), (1, 10), (5, 5), (9, 15), (13, 0)]
    sim_dauer = 15
    t = np.arange(0, sim_dauer, dt)
    
    zustand_ga = 0
    zustand_zn = 0
    mess_ga = []
    mess_zn = []
    setpunkte = []
    
    for zeit in t:
        # Sollwert
        setp = 0
        for set_zeit, set_wert in profil:
            if zeit >= set_zeit:
                setp = set_wert
        setpunkte.append(setp)
        
        # GA-PID
        pid_ga = PIDRegler(ga_params.Kp, ga_params.Ki, ga_params.Kd, setp)
        stell_ga = pid_ga.berechnen(zustand_ga, dt)
        zustand_ga = system(zustand_ga, stell_ga, dt)
        mess_ga.append(zustand_ga[0] if isinstance(zustand_ga, tuple) else zustand_ga)
        
        # ZN-PID
        pid_zn = PIDRegler(zn_params.Kp, zn_params.Ki, zn_params.Kd, setp)
        stell_zn = pid_zn.berechnen(zustand_zn, dt)
        zustand_zn = system(zustand_zn, stell_zn, dt)
        mess_zn.append(zustand_zn[0] if isinstance(zustand_zn, tuple) else zustand_zn)
    
    # Plot
    plt.figure(figsize=(12, 6))
    plt.plot(t, mess_ga, 'b-', label='GA-PID', linewidth=1)
    plt.plot(t, mess_zn, 'g-', label='Ziegler-Nichols', linewidth=1)
    plt.plot(t, setpunkte, 'r--', label='Sollwert', linewidth=2)
    plt.xlabel('Zeit (s)')
    plt.ylabel('Regelgröße')
    plt.title('Vergleich: GA-PID vs. Ziegler-Nichols')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()
    
    # MSE berechnen
    mse_ga = np.mean((np.array(setpunkte) - np.array(mess_ga))**2)
    mse_zn = np.mean((np.array(setpunkte) - np.array(mess_zn))**2)
    
    print(f"\nMSE GA-PID: {mse_ga:.4f}")
    print(f"MSE Ziegler-Nichols: {mse_zn:.4f}")
    print(f"Verbesserung: {(mse_zn - mse_ga)/mse_zn*100:.1f}%")


# ============================================================================
# EINFACHES ONLINE-OPTIMIERUNGSBEISPIEL
# ============================================================================

class OnlineGAPID:
    """
    Online-GA-PID: Optimiert während des Betriebs
    """
    
    def __init__(self, 
                 Kp_init: float = 1.0,
                 Ki_init: float = 0.1,
                 Kd_init: float = 0.05,
                 setpoint: float = 0,
                 sample_time: float = 0.01):
        
        self.Kp = Kp_init
        self.Ki = Ki_init
        self.Kd = Kd_init
        self.setpoint = setpoint
        self.sample_time = dt = sample_time
        
        # PID-Zustand
        self.last_error = 0
        self.integral = 0
        self.last_output = 0
        
        # Historie für Fitness-Berechnung
        self.error_history = deque(maxlen=500)
        self.output_history = deque(maxlen=500)
        
        # GA für Online-Optimierung
        self.ga = GenetischerAlgorithmus(
            population_groesse=20,
            mutation_rate=0.1,
            crossover_rate=0.8,
            elitismus_anteil=0.1,
            param_grenzen={
                'Kp': (0.1, 5.0),
                'Ki': (0.0, 2.0),
                'Kd': (0.0, 1.0)
            }
        )
        
        # Startpopulation mit aktuellen Parametern
        start = PIDIndividuum(Kp_init, Ki_init, Kd_init)
        self.ga.initialisiere_population(start)
        
        self.optimierungs_intervall = 50
        self.step_count = 0
        
    def berechnen(self, messwert: float, zeit: float = None) -> float:
        """Berechnet Stellgröße und optimiert periodisch"""
        dt = self.sample_time
        
        # PID-Berechnung
        error = self.setpoint - messwert
        self.error_history.append(error)
        
        self.integral += error * dt
        derivative = (error - self.last_error) / dt
        
        output = (self.Kp * error + 
                 self.Ki * self.integral + 
                 self.Kd * derivative)
        
        self.last_error = error
        self.last_output = output
        self.output_history.append(output)
        
        # Periodische Optimierung
        self.step_count += 1
        if self.step_count % self.optimierungs_intervall == 0:
            self._optimiere()
        
        return output
    
    def _optimiere(self):
        """Führt eine GA-Optimierung durch"""
        if len(self.error_history) < 100:
            return
        
        # Fitness-Funktion basierend auf letzen Fehlern
        def fitness(Kp, Ki, Kd):
            # Simuliere Performance mit diesen Parametern
            fehler = np.array(list(self.error_history)[-200:])
            mse = np.mean(fehler**2)
            return 1.0 / (mse + 1e-6)
        
        # Eine GA-Generation evolvieren
        bestes = self.ga.evolviere(fitness)
        
        # Sanfte Übernahme neuer Parameter
        lernrate = 0.3
        self.Kp = self.Kp * (1 - lernrate) + bestes.Kp * lernrate
        self.Ki = self.Ki * (1 - lernrate) + bestes.Ki * lernrate
        self.Kd = self.Kd * (1 - lernrate) + bestes.Kd * lernrate
        
        print(f"Online-Optimierung: Kp={self.Kp:.3f}, Ki={self.Ki:.3f}, Kd={self.Kd:.3f}")


# ============================================================================
# HAUPTFUNKTION
# ============================================================================

if __name__ == "__main__":
   
    #beispiel_pt2_optimierung()       
    
    beispiel_nichtlinear_optimierung()
        
    #beispiel_totzeit_optimierung()
    
    #vergleich_mit_ziegler_nichols()
