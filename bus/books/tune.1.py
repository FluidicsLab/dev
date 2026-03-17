
"""
Adaptiver PID-Regler mit Genetischem Algorithmus (GA-PID)
==========================================================
Der genetische Algorithmus optimiert die PID-Parameter (Kp, Ki, Kd)
kontinuierlich während des Betriebs.
"""

import numpy as np
import matplotlib.pyplot as plt
from collections import deque
import time
import random
from dataclasses import dataclass, field
from typing import List, Tuple, Callable, Optional
import copy

@dataclass
class Individual:
    """Ein Individuum im genetischen Algorithmus (Satz von PID-Parametern)"""
    Kp: float
    Ki: float
    Kd: float
    fitness: float = 0.0
    generation: int = 0
    
    def get_params(self) -> Tuple[float, float, float]:
        return (self.Kp, self.Ki, self.Kd)
    
    def __str__(self):
        return f"Kp={self.Kp:.4f}, Ki={self.Ki:.4f}, Kd={self.Kd:.4f}, Fitness={self.fitness:.6f}"

class GeneticAlgorithm:
    """
    Genetischer Algorithmus zur PID-Parameter-Optimierung
    
    Features:
    - Tournament-Selektion
    - Blending Crossover (BLX-α)
    - Gaussian Mutation
    - Elitismus
    - Adaptives Mutationsrate
    """
    
    def __init__(self, 
                 population_size: int = 50,
                 mutation_rate: float = 0.1,
                 crossover_rate: float = 0.8,
                 elitism_ratio: float = 0.1,
                 tournament_size: int = 3,
                 generations: int = 10,
                 param_bounds: dict = None):
        """
        Initialisiert den genetischen Algorithmus
        
        Args:
            population_size: Anzahl der Individuen pro Generation
            mutation_rate: Wahrscheinlichkeit für Mutation (0-1)
            crossover_rate: Wahrscheinlichkeit für Crossover (0-1)
            elitism_ratio: Anteil der besten Individuen, die überleben
            tournament_size: Größe des Turniers für Selektion
            param_bounds: Grenzen für Parameter { 'Kp': (min,max), 'Ki': (min,max), 'Kd': (min,max) }
        """
        self.population_size = population_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism_count = max(1, int(population_size * elitism_ratio))
        self.tournament_size = tournament_size
        self.generations = generations
        
        # Standard-Parameter-Grenzen
        self.param_bounds = param_bounds or {
            'Kp': (0.0, 10.0),
            'Ki': (0.0, 5.0),
            'Kd': (0.0, 2.0)
        }
        
        self.population: List[Individual] = []
        self.generation = 0
        self.best_individual: Optional[Individual] = None
        self.fitness_history: List[float] = []
        self.avg_fitness_history: List[float] = []
        
        # Adaptive Parameter
        self.base_mutation_rate = mutation_rate
        self.stagnation_counter = 0
        self.last_best_fitness = 0
        
    def initialize_population(self, seed_individual: Optional[Individual] = None):
        """
        Initialisiert die Population
        
        Args:
            seed_individual: Optional Start-Individuum (z.B. manuell eingestellte Parameter)
        """
        self.population = []
        
        # Wenn ein Seed-Individuum gegeben ist, füge es hinzu
        if seed_individual:
            self.population.append(seed_individual)
            
        # Fülle den Rest mit zufälligen Individuen
        while len(self.population) < self.population_size:
            individual = Individual(
                Kp=np.random.uniform(*self.param_bounds['Kp']),
                Ki=np.random.uniform(*self.param_bounds['Ki']),
                Kd=np.random.uniform(*self.param_bounds['Kd'])
            )
            self.population.append(individual)
    
    def evaluate_fitness(self, individual: Individual, 
                         evaluate_func: Callable[[float, float, float], float]):
        """
        Bewertet die Fitness eines Individuums
        
        Args:
            individual: Zu bewertendes Individuum
            evaluate_func: Funktion, die (Kp, Ki, Kd) annimmt und Fitness zurückgibt
                          (Höhere Fitness = besser)
        """
        individual.fitness = evaluate_func(individual.Kp, individual.Ki, individual.Kd)
        return individual.fitness
    
    def evaluate_population(self, evaluate_func: Callable[[float, float, float], float]):
        """
        Bewertet alle Individuen in der Population
        """
        for individual in self.population:
            self.evaluate_fitness(individual, evaluate_func)
    
    def tournament_selection(self) -> Individual:
        """
        Turnier-Selektion: Wählt das beste Individuum aus einer zufälligen Auswahl
        
        Returns:
            Ausgewähltes Individuum
        """
        tournament = random.sample(self.population, self.tournament_size)
        return max(tournament, key=lambda ind: ind.fitness)
    
    def crossover(self, parent1: Individual, parent2: Individual) -> Tuple[Individual, Individual]:
        """
        BLX-α Crossover (Blend Crossover)
        Erzeugt Kinder durch lineare Interpolation der Eltern
        """
        if random.random() > self.crossover_rate:
            # Kein Crossover: Eltern direkt kopieren
            return copy.deepcopy(parent1), copy.deepcopy(parent2)
        
        alpha = 0.5  # Blend-Faktor
        
        child1 = Individual(0, 0, 0)
        child2 = Individual(0, 0, 0)
        
        for param in ['Kp', 'Ki', 'Kd']:
            p1_val = getattr(parent1, param)
            p2_val = getattr(parent2, param)
            
            # Intervall berechnen
            min_val = min(p1_val, p2_val)
            max_val = max(p1_val, p2_val)
            interval = max_val - min_val
            
            # Erweitertes Intervall für Exploration
            lower = min_val - alpha * interval
            upper = max_val + alpha * interval
            
            # Kinder im erweiterten Intervall erzeugen
            c1_val = np.random.uniform(lower, upper)
            c2_val = np.random.uniform(lower, upper)
            
            # Parameter in Grenzen halten
            bounds = self.param_bounds[param]
            setattr(child1, param, np.clip(c1_val, bounds[0], bounds[1]))
            setattr(child2, param, np.clip(c2_val, bounds[0], bounds[1]))
        
        child1.generation = self.generation + 1
        child2.generation = self.generation + 1
        
        return child1, child2
    
    def mutate(self, individual: Individual):
        """
        Gaussian Mutation mit adaptiver Rate
        """
        # Adaptive Mutationsrate basierend auf Stagnation
        current_mutation_rate = self.mutation_rate
        if self.stagnation_counter > 5:
            current_mutation_rate *= 1.5  # Erhöhe Mutation bei Stagnation
        
        for param in ['Kp', 'Ki', 'Kd']:
            if random.random() < current_mutation_rate:
                current_val = getattr(individual, param)
                bounds = self.param_bounds[param]
                
                # Standardabweichung = 10% des Wertebereichs
                std = (bounds[1] - bounds[0]) * 0.1
                
                # Gaussian Mutation
                new_val = current_val + np.random.normal(0, std)
                
                # In Grenzen halten
                setattr(individual, param, np.clip(new_val, bounds[0], bounds[1]))
        
        return individual
    
    def evolve(self, evaluate_func: Callable[[float, float, float], float]) -> Individual:
        """
        Erzeugt die nächste Generation
        
        Args:
            evaluate_func: Fitness-Funktion
            
        Returns:
            Bestes Individuum der neuen Generation
        """
        # Fitness der aktuellen Population bewerten
        self.evaluate_population(evaluate_func)
        
        # Nach Fitness sortieren
        self.population.sort(key=lambda ind: ind.fitness, reverse=True)
        
        # Bestes Individuum speichern
        current_best = self.population[0]
        if not self.best_individual or current_best.fitness > self.best_individual.fitness:
            self.best_individual = copy.deepcopy(current_best)
            self.stagnation_counter = 0
        else:
            self.stagnation_counter += 1
        
        # Fitness-Historie aktualisieren
        self.fitness_history.append(self.best_individual.fitness)
        self.avg_fitness_history.append(np.mean([ind.fitness for ind in self.population]))
        
        # Elitismus: Die besten Individuen direkt übernehmen
        new_population = self.population[:self.elitism_count]
        
        # Restliche Individuen durch Selektion, Crossover und Mutation erzeugen
        while len(new_population) < self.population_size:
            # Eltern auswählen
            parent1 = self.tournament_selection()
            parent2 = self.tournament_selection()
            
            # Crossover
            child1, child2 = self.crossover(parent1, parent2)
            
            # Mutation
            child1 = self.mutate(child1)
            child2 = self.mutate(child2)
            
            new_population.append(child1)
            if len(new_population) < self.population_size:
                new_population.append(child2)
        
        self.population = new_population
        self.generation += 1
        
        return self.best_individual
    
    def get_statistics(self) -> dict:
        """Gibt Statistiken über den GA zurück"""
        return {
            'generation': self.generation,
            'best_fitness': self.best_individual.fitness if self.best_individual else 0,
            'avg_fitness': np.mean([ind.fitness for ind in self.population]),
            'population_size': len(self.population),
            'mutation_rate': self.mutation_rate,
            'stagnation': self.stagnation_counter
        }


class GeneticAdaptivePID:
    """
    Adaptiver PID-Regler mit genetischem Algorithmus zur Online-Optimierung
    
    Der GA optimiert die PID-Parameter kontinuierlich während des Betriebs,
    basierend auf der Regelgüte der letzten N Zeitschritte.
    """
    
    def __init__(self, 
                 Kp_init: float = 1.0,
                 Ki_init: float = 0.1,
                 Kd_init: float = 0.05,
                 setpoint: float = 0,
                 sample_time: float = 0.01,
                 output_limits: Tuple[Optional[float], Optional[float]] = (None, None),
                 ga_params: dict = None):
        """
        Initialisiert den GA-basierten adaptiven PID-Regler
        
        Args:
            Kp_init: Initialer Proportionalverstärkung
            Ki_init: Initialer Integralverstärkung
            Kd_init: Initialer Differenzialverstärkung
            setpoint: Sollwert
            sample_time: Abtastzeit
            output_limits: Stellgrößenbegrenzung (min, max)
            ga_params: Parameter für den genetischen Algorithmus
        """
        # PID-Zustand
        self.Kp = Kp_init
        self.Ki = Ki_init
        self.Kd = Kd_init
        self.setpoint = setpoint
        self.sample_time = sample_time
        self.output_limits = output_limits
        
        # Interne PID-Variablen
        self.last_error = 0
        self.integral = 0
        self.last_output = 0
        self.last_time = time.time()
        
        # Filter für Ableitung
        self.derivative_filter = 0.1
        self.filtered_derivative = 0
        
        # Anti-Windup
        self.integral_limit = None
        self.anti_windup = True
        
        # Historie für Fitness-Berechnung
        self.error_history = deque(maxlen=500)
        self.output_history = deque(maxlen=500)
        self.time_history = deque(maxlen=500)
        self.setpoint_history = deque(maxlen=500)
        
        # GA-Konfiguration
        default_ga_params = {
            'population_size': 30,
            'mutation_rate': 0.1,
            'crossover_rate': 0.8,
            'elitism_ratio': 0.1,
            'tournament_size': 3,
            'param_bounds': {
                'Kp': (0.1, 10.0),
                'Ki': (0.0, 5.0),
                'Kd': (0.0, 2.0)
            }
        }
        
        if ga_params:
            default_ga_params.update(ga_params)
        
        self.ga_params = default_ga_params
        self.ga = GeneticAlgorithm(**self.ga_params)
        
        # Initialisiere GA mit manuellen Startparametern
        seed = Individual(Kp_init, Ki_init, Kd_init)
        self.ga.initialize_population(seed)
        
        # Optimierungssteuerung
        self.optimization_interval = 50  # Schritte zwischen GA-Optimierungen
        self.step_count = 0
        self.evaluation_window = 200  # Fenster für Fitness-Berechnung
        self.online_optimization = True
        
        # Performance-Tracking
        self.parameter_history = deque(maxlen=1000)
        self.performance_history = deque(maxlen=1000)
        
        # Beste Parameter speichern
        self.best_Kp = Kp_init
        self.best_Ki = Ki_init
        self.best_Kd = Kd_init
        
    def calculate(self, feedback: float, current_time: Optional[float] = None) -> float:
        """
        Berechnet die Stellgröße mit GA-Optimierung
        
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
            error = self.setpoint - feedback
            self.error_history.append(error)
            self.setpoint_history.append(self.setpoint)
            self.time_history.append(current_time)
            
            # Online-Optimierung durchführen
            if self.online_optimization and self.step_count % self.optimization_interval == 0:
                self._optimize_parameters()
            
            # PID-Berechnung
            self.integral += error * dt
            if self.anti_windup and self.integral_limit:
                self.integral = np.clip(self.integral, -self.integral_limit, self.integral_limit)
            
            derivative = (error - self.last_error) / dt
            self.filtered_derivative = (self.derivative_filter * derivative + 
                                       (1 - self.derivative_filter) * self.filtered_derivative)
            
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
            
            # Parameter-Historie (für Analyse)
            self.parameter_history.append((self.Kp, self.Ki, self.Kd))
            
            self.step_count += 1
            
            return output
        
        return self.last_output
    
    def _optimize_parameters(self):
        """
        Führt eine Optimierung mit dem genetischen Algorithmus durch
        """
        if len(self.error_history) < self.evaluation_window:
            return
        
        # Definiere Fitness-Funktion basierend auf aktuellen Daten
        def fitness_function(Kp: float, Ki: float, Kd: float) -> float:
            """
            Berechnet die Fitness eines Parametersatzes
            (Höhere Fitness = besser)
            """
            # Letzte N Fehler für Bewertung verwenden
            errors = list(self.error_history)[-self.evaluation_window:]
            
            if not errors:
                return 0
            
            # Verschiedene Metriken kombinieren
            mse = np.mean(np.square(errors))  # Mean Squared Error
            mae = np.mean(np.abs(errors))      # Mean Absolute Error
            max_error = np.max(np.abs(errors)) # Maximaler Fehler
            
            # Überschwingen erkennen (wenn Fehler das Vorzeichen wechselt)
            overshoot = 0
            if len(errors) > 10:
                # Prüfe auf Vorzeichenwechsel (Überschwingen)
                sign_changes = sum(1 for i in range(1, len(errors)) 
                                  if errors[i-1] * errors[i] < 0)
                overshoot = sign_changes / len(errors)
            
            # Oszillation erkennen
            oscillation = 0
            if len(errors) > 20:
                # Autokorrelation als Oszillationsmaß
                errors_np = np.array(errors[-100:])
                if len(errors_np) > 10:
                    acf = np.correlate(errors_np - np.mean(errors_np), 
                                      errors_np - np.mean(errors_np), mode='full')
                    if len(acf) > 10:
                        oscillation = np.std(acf[len(acf)//2:]) / (np.std(errors_np) + 1e-6)
            
            # Kombinierte Fitness (je kleiner die Fehler, desto höher die Fitness)
            # Gewichtung der verschiedenen Metriken
            w1, w2, w3, w4, w5 = 1.0, 0.5, 0.3, 0.5, 0.3
            
            # Normalisierte Metriken (kleinere Werte sind besser)
            normalized_mse = mse / (abs(self.setpoint) + 1e-6)
            normalized_mae = mae / (abs(self.setpoint) + 1e-6)
            normalized_max = max_error / (abs(self.setpoint) + 1e-6)
            
            # Fitness = 1 / (gewichtete Summe der Fehlermetriken)
            # + kleine Konstante zur Vermeidung von Division durch Null
            fitness = 1.0 / (w1 * normalized_mse + 
                            w2 * normalized_mae + 
                            w3 * normalized_max +
                            w4 * overshoot +
                            w5 * oscillation + 1e-6)
            
            return fitness
        
        # GA eine Generation evolvieren
        best = self.ga.evolve(fitness_function)
        
        # Neue Parameter übernehmen (mit Lernrate)
        learning_rate = 0.3  # Wie schnell neue Parameter übernommen werden
        
        self.Kp = self.Kp * (1 - learning_rate) + best.Kp * learning_rate
        self.Ki = self.Ki * (1 - learning_rate) + best.Ki * learning_rate
        self.Kd = self.Kd * (1 - learning_rate) + best.Kd * learning_rate
        
        # Beste Parameter speichern
        self.best_Kp = best.Kp
        self.best_Ki = best.Ki
        self.best_Kd = best.Kd
        
        # Performance speichern
        self.performance_history.append({
            'generation': self.ga.generation,
            'fitness': best.fitness,
            'Kp': self.Kp,
            'Ki': self.Ki,
            'Kd': self.Kd
        })
        
        if self.ga.generation % 5 == 0:
            stats = self.ga.get_statistics()
            print(f"Gen {stats['generation']}: Fitness={stats['best_fitness']:.6f}, "
                  f"Kp={self.Kp:.3f}, Ki={self.Ki:.3f}, Kd={self.Kd:.3f}")
    
    def get_current_parameters(self) -> dict:
        """Gibt die aktuellen PID-Parameter zurück"""
        return {
            'Kp': self.Kp,
            'Ki': self.Ki,
            'Kd': self.Kd,
            'generation': self.ga.generation,
            'best_fitness': self.ga.best_individual.fitness if self.ga.best_individual else 0
        }
    
    def get_ga_statistics(self) -> dict:
        """Gibt Statistiken des genetischen Algorithmus zurück"""
        return self.ga.get_statistics()
    
    def reset(self):
        """Setzt den Regler zurück"""
        self.last_error = 0
        self.integral = 0
        self.last_output = 0
        self.last_time = time.time()
        self.filtered_derivative = 0
        self.error_history.clear()
        self.output_history.clear()
        self.time_history.clear()
        self.setpoint_history.clear()
        self.parameter_history.clear()
        self.performance_history.clear()
        self.step_count = 0


class OfflineGAPIDOptimizer:
    """
    Offline-Optimierung eines PID-Reglers mit genetischem Algorithmus
    
    Verwendet ein Modell der Regelstrecke zur Simulation und Optimierung,
    bevor der Regler online eingesetzt wird.
    """
    
    def __init__(self, 
                 plant_model: Callable,
                 sample_time: float = 0.01,
                 ga_params: dict = None):
        """
        Args:
            plant_model: Funktion (state, control, dt) -> new_state
            sample_time: Abtastzeit für Simulation
            ga_params: Parameter für GA
        """
        self.plant_model = plant_model
        self.sample_time = sample_time
        
        # GA initialisieren
        default_ga_params = {
            'population_size': 100,
            'mutation_rate': 0.15,
            'crossover_rate': 0.85,
            'elitism_ratio': 0.1,
            'tournament_size': 5,
            'generations': 30,
            'param_bounds': {
                'Kp': (0.0, 20.0),
                'Ki': (0.0, 10.0),
                'Kd': (0.0, 5.0)
            }
        }
        if ga_params:
            default_ga_params.update(ga_params)
        
        self.ga = GeneticAlgorithm(**default_ga_params)
        self.ga.initialize_population()
        
    def simulate_pid(self, 
                     Kp: float, 
                     Ki: float, 
                     Kd: float, 
                     setpoint_profile: List[Tuple[float, float]],
                     runtime: float,
                     noise: float = 0.0) -> dict:
        """
        Simuliert einen PID-Regler mit gegebenen Parametern
        
        Args:
            Kp, Ki, Kd: PID-Parameter
            setpoint_profile: Liste von (zeit, setpoint) Tupeln
            runtime: Simulationsdauer
            noise: Messrauschen
            
        Returns:
            Dictionary mit Simulationsergebnissen
        """
        dt = self.sample_time
        t = np.arange(0, runtime, dt)
        
        state = 0
        measurements = []
        setpoints = []
        errors = []
        
        last_error = 0
        integral = 0
        
        for time_point in t:
            
            current_setpoint = 0
            for set_time, set_value in setpoint_profile:
                if time_point >= set_time:
                    current_setpoint = set_value
            
            setpoints.append(current_setpoint)
            
            if isinstance(state, (int, float)):
                error = current_setpoint - state
            else:
                error = current_setpoint - state[0]
            errors.append(error)
            
            integral += error * dt
            derivative = (error - last_error) / dt if dt > 0 else 0
            
            control = Kp * error + Ki * integral + Kd * derivative
            
            if isinstance(state, (int, float)): 
                measurement = state + np.random.normal(0, noise)
            else:
                measurement = state[1] + np.random.normal(0, noise)
            measurements.append(measurement)
            
            # 
            state = self.plant_model(state, control, dt)
            last_error = error
        
        return {
            't': t,
            'measurements': measurements,
            'setpoints': setpoints,
            'errors': errors
        }
    
    def fitness_function(self, Kp: float, Ki: float, Kd: float) -> float:
        """
        Fitness-Funktion für offline Optimierung
        Simuliert einen Regelvorgang und bewertet die Performance
        """
        # Test-Szenario definieren
        setpoint_profile = [
            (0, 0),
            (1, 10),
            (5, 5),
            (8, 15),
            (12, 0)
        ]
        
        # Simulation durchführen
        results = self.simulate_pid(Kp, Ki, Kd, setpoint_profile, runtime=15, noise=0.01)
        
        errors = np.array(results['errors'])
        
        # Verschiedene Metriken
        mse = np.mean(errors**2)
        mae = np.mean(np.abs(errors))
        max_error = np.max(np.abs(errors))
        
        # Überschwingen bewerten
        overshoot_penalty = 0
        for i in range(1, len(errors)):
            if errors[i-1] * errors[i] < 0:  # Vorzeichenwechsel
                overshoot_penalty += abs(errors[i])
        
        # Einschwingzeit bewerten (wann bleibt Fehler unter 2%)
        settling_time = len(errors)
        for i in range(len(errors)-1, 0, -1):
            if abs(errors[i]) > 0.02 * abs(setpoint_profile[0][1]):  # 2% Toleranz
                settling_time = i
                break
        
        # Kombinierte Fitness (höher = besser)
        fitness = 1.0 / (mse + 0.1 * mae + 0.05 * max_error + 
                        0.01 * overshoot_penalty + 0.001 * settling_time + 1e-6)
        
        return fitness
    
    def optimize(self, generations: int = 50) -> Individual:
        """
        Führt die Optimierung durch
        
        Args:
            generations: Anzahl der Generationen
            
        Returns:
            Bestes Individuum (optimale PID-Parameter)
        """
        print("Starte offline GA-PID Optimierung...")
        print(f"Population: {self.ga.population_size}, Generationen: {generations}")
        print("-" * 60)
        
        for gen in range(generations):
            best = self.ga.evolve(self.fitness_function)
            
            if (gen + 1) % 5 == 0:
                stats = self.ga.get_statistics()
                print(f"generation {gen+1} best fitness = {stats['best_fitness']:.6f}, "
                      f"avg fitness = {stats['avg_fitness']:.6f}")
                print(f"best Kp={best.Kp:.3f}, Ki={best.Ki:.3f}, Kd={best.Kd:.3f}")
        
        print("-" * 60)
        print(f"Optimierung abgeschlossen nach {generations} Generationen")
        print(f"Optimale PID-Parameter: {best}")
        
        return best


# ============== TEST- UND DEMO-FUNKTIONEN ==============

def example_pt2_system(state, control, dt):
    """PT2-System (schwingungsfähig)"""
    omega = 2.0
    D = 0.3
    
    if isinstance(state, (int, float)):
        x1, x2 = state, 0
    else:
        x1, x2 = state
    
    dx1 = x2
    dx2 = -2*D*omega*x2 - omega**2*x1 + omega**2*control
    
    x1_new = x1 + dx1 * dt
    x2_new = x2 + dx2 * dt
    
    return (x1_new, x2_new)


def example_nonlinear_system(state, control, dt):
    """Nichtlineares System mit Sättigung"""
    # Sättigung
    control = np.clip(control, -20, 20)
    
    # Nichtlineare Kennlinie
    if control > 0:
        return state + control * dt * 1.5
    else:
        return state + control * dt * 0.8


def run_online_demo():
    """Demonstriert den Online-GA-PID"""
    print("\n" + "="*60)
    print("ONLINE GA-PID DEMO")
    print("="*60)
    
    # PID mit GA initialisieren
    pid = GeneticAdaptivePID(
        Kp_init=1.0,
        Ki_init=0.2,
        Kd_init=0.05,
        setpoint=10,
        sample_time=0.01,
        ga_params={
            'population_size': 20,
            'mutation_rate': 0.1,
            'param_bounds': {
                'Kp': (0.1, 5.0),
                'Ki': (0.0, 2.0),
                'Kd': (0.0, 1.0)
            }
        }
    )

    noise = 0.0
    
    # simulation
    dt = pid.sample_time
    runtime = 20
    t = np.arange(0, runtime, dt)
    
    state = 0
    measurements = []
    setpoints = []
    controls = []
    
    Kp = []
    Ki = []
    Kd = []
    
    for i, time_point in enumerate(t):
        
        current_setpoint = 8
        if time_point < 5:
            current_setpoint = 5
        elif time_point < 10:
            current_setpoint = 10
        elif time_point < 15:
            current_setpoint = 3

        pid.setpoint = current_setpoint
        setpoints.append(current_setpoint)

        if isinstance(state, (int, float)): 
            measurement = state + np.random.normal(0, noise)
        else:
            measurement = state[1] + np.random.normal(0, noise)
        measurements.append(measurement)
        
        control = pid.calculate(measurement, time_point)
        controls.append(control)
        
        params = pid.get_current_parameters()
        Kp.append(params['Kp'])
        Ki.append(params['Ki'])
        Kd.append(params['Kd'])
        
        if i % 100 == 0:            
            print(f"t={time_point:.1f}: {params}")

    return {
        't': t,
        'measurements': measurements,
        'setpoints': setpoints,
        'controls': controls,
        'history': [Kp, Ki, Kd],
        'pid': pid
    }


def plot_results(results):
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    ax1.plot(results["t"], results["measurements"], 'b-', label='processvalue')
    ax1.plot(results["t"], results["setpoints"], 'r--', label='setpoint')
    ax1.set_ylabel('control')
    ax1.legend()
    ax1.grid(True)
    ax1.set_title('online ga')
    
    ax2.plot(results["t"], results["history"][0], 'g-', label='Kp')
    ax2.set_ylabel('Kp')
    ax2.legend()
    ax2.grid(True)
    
    # GA-Fitness-Verlauf
    #if hasattr(pid, 'performance_history') and pid.performance_history:
    #    generations = [p['generation'] for p in pid.performance_history]
    #    fitness = [p['fitness'] for p in pid.performance_history]
    #    ax3.plot(generations, fitness, 'm-', label='Fitness')
    #    ax3.set_xlabel('Generation')
    #    ax3.set_ylabel('Fitness')
    #    ax3.legend()
    #    ax3.grid(True)
    
    plt.tight_layout()
    plt.show()


def run_offline_demo():

    generations = 20
    
    optimizer = OfflineGAPIDOptimizer(
        plant_model=example_pt2_system,
        sample_time=0.01,
        ga_params={
            'population_size': 50,
            'generations': generations
        }
    )
    
    best = optimizer.optimize(generations=generations)
    
    print(f"\nOptimierte Parameter: {best}")
        
    #
    initial = Individual(
        Kp=np.random.uniform(0.5, 2),
        Ki=np.random.uniform(0.1, 0.5),
        Kd=np.random.uniform(0.01, 0.1)
    )
    
    setpoint_profile = [(0, 0), (1, 10), (5, 5), (8, 15), (12, 0)]
    
    for name, ind in [
        ("initial  ", initial), 
        ("optimized", best)]:
        
        results = optimizer.simulate_pid(
            ind.Kp, ind.Ki, ind.Kd, 
            setpoint_profile, runtime=15, noise=0.01
        )
        
        mse = np.mean(np.square(results['errors']))
        
        print(f"{name} MSE {mse:.4f}, Kp {ind.Kp:.3f}, Ki {ind.Ki:.3f}, Kd {ind.Kd:.3f}")


def run_comparison_demo():
    """Vergleicht GA-PID mit klassischem PID"""
    print("\n" + "="*60)
    print("VERGLEICH: GA-PID vs. KLASSISCHER PID")
    print("="*60)
    
    # GA-PID
    ga_pid = GeneticAdaptivePID(
        Kp_init=1.0,
        Ki_init=0.2,
        Kd_init=0.05,
        setpoint=10,
        sample_time=0.01
    )
    
    # Klassischer PID (manuell eingestellt)
    class ClassicPID:
        def __init__(self, Kp, Ki, Kd, setpoint):
            self.Kp, self.Ki, self.Kd = Kp, Ki, Kd
            self.setpoint = setpoint
            self.last_error = 0
            self.integral = 0
            
        def calculate(self, feedback, dt):
            error = self.setpoint - feedback
            self.integral += error * dt
            derivative = (error - self.last_error) / dt
            output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
            self.last_error = error
            return output
    
    classic_pid = ClassicPID(Kp=1.5, Ki=0.3, Kd=0.08, setpoint=10)
    
    # Simulation
    dt = 0.01
    runtime = 20
    t = np.arange(0, runtime, dt)
    
    ga_measurements = []
    classic_measurements = []
    
    state_ga = 0
    state_classic = 0
    
    for time_point in t:
        # Sollwert-Profil
        if time_point < 3:
            ga_pid.setpoint = 5
            classic_pid.setpoint = 5
        elif time_point < 7:
            ga_pid.setpoint = 12
            classic_pid.setpoint = 12
        elif time_point < 12:
            ga_pid.setpoint = 3
            classic_pid.setpoint = 3
        else:
            ga_pid.setpoint = 8
            classic_pid.setpoint = 8
        
        # GA-PID
        output_ga = ga_pid.calculate(state_ga, time_point)
        state_ga = example_nonlinear_system(state_ga, output_ga, dt)
        ga_measurements.append(state_ga if isinstance(state_ga, (int, float)) else state_ga[0])
        
        # Classic PID
        output_classic = classic_pid.calculate(state_classic, dt)
        state_classic = example_nonlinear_system(state_classic, output_classic, dt)
        classic_measurements.append(state_classic if isinstance(state_classic, (int, float)) else state_classic[0])
    
    # Plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    ax1.plot(t, ga_measurements, 'b-', label='GA-PID', linewidth=1)
    ax1.plot(t, classic_measurements, 'g-', label='Klassischer PID', linewidth=1)
    ax1.plot(t, [ga_pid.setpoint]*len(t), 'r--', label='Sollwert', linewidth=2)
    ax1.set_ylabel('Regelgröße')
    ax1.legend()
    ax1.grid(True)
    ax1.set_title('GA-PID vs. Klassischer PID')
    
    # Fehler
    ga_error = np.array(ga_measurements) - np.array([ga_pid.setpoint]*len(t))
    classic_error = np.array(classic_measurements) - np.array([classic_pid.setpoint]*len(t))
    
    ax2.plot(t, ga_error, 'b-', label='GA-PID Fehler', alpha=0.7)
    ax2.plot(t, classic_error, 'g-', label='Klassischer PID Fehler', alpha=0.7)
    ax2.set_xlabel('Zeit (s)')
    ax2.set_ylabel('Regelfehler')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    plt.show()
    
    # Metriken
    ga_mse = np.mean(ga_error**2)
    classic_mse = np.mean(classic_error**2)
    
    print(f"\nPerformance-Vergleich:")
    print(f"GA-PID MSE: {ga_mse:.4f}")
    print(f"Klassischer PID MSE: {classic_mse:.4f}")
    print(f"Verbesserung: {(classic_mse - ga_mse)/classic_mse*100:.1f}%")

if __name__ == "__main__":

    import os
    os.system("cls")
    
    #results = run_online_demo()
    #plot_results(results)
    
    run_offline_demo()

    #run_comparison_demo()
    