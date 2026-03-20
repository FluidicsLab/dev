import time
import numpy as np
from collections import deque

class AdaptivePID:
    
    def __init__(self, kp=1.0, ki=0.1, kd=0.05, setpoint=50.0, sample_time=0.1):
        
        # PID-Parameter
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        # Soll- und Istwert
        self.setpoint = np.clip(setpoint, 0, 100)
        self.last_input = 0
        
        # Fehlerspeicher
        self.error_sum = 0
        self.last_error = 0
        self.last_time = time.time()
        self.sample_time = sample_time
        
        # Begrenzungen (0-100%)
        self.output_limits = (0, 100)
        
        # Für adaptive Parameter
        self.error_history = deque(maxlen=10)
        self.performance_history = deque(maxlen=50)
        self.adaptation_rate = 0.001
       
        self.min_kp = 0.1
        self.max_kp = 20.0

        self.min_ki = 0.0
        self.max_ki = 1.0
        
        self.min_kd = 0.0
        self.max_kd = 1.0
        
    def compute(self, input_value):
        """
        Berechnet den Ausgangswert basierend auf dem Eingang
        
        Args:
            input_value: Aktueller Istwert (0-100%)
            
        Returns:
            float: Stellgröße (0-100%)
        """
        # Zeit seit letzter Berechnung
        current_time = time.time()
        dt = current_time - self.last_time
        
        #if dt > self.sample_time:
        #    self.last_time = current_time
        #    return None
        
        dt = 0.1
            
        # Istwert begrenzen
        input_value = np.clip(input_value, 0, 100)
        
        # Fehler berechnen
        error = self.setpoint - input_value
        
        # Fehler für Historie speichern
        self.error_history.append(error)
        
        # P-Anteil
        p_term = self.kp * error
        
        # I-Anteil (mit Anti-Windup)
        self.error_sum += error * dt
        self.error_sum = np.clip(self.error_sum, -100/self.ki if self.ki > 0 else -100, 100/self.ki if self.ki > 0 else 100)
        i_term = self.ki * self.error_sum
        
        # D-Anteil (mit Filterung)
        if dt > 0:
            derivative = (error - self.last_error) / dt
            d_term = self.kd * derivative
        else:
            d_term = 0
            
        # Ausgang berechnen
        output = p_term + i_term + d_term
        
        # Ausgang begrenzen (0-100%)
        output = np.clip(output, self.output_limits[0], self.output_limits[1])
        
        # Zustände speichern
        self.last_input = input_value
        self.last_error = error
        self.last_time = current_time

        print(f"{error:.3f} {output}")
        
        return output
    
    def adapt_parameters(self):
        """
        Passt die PID-Parameter adaptiv an die Regelgüte an
        """
        if len(self.error_history) < 5:
            return
            
        # Performanz berechnen
        current_error = abs(self.last_error)
        mean_error = np.mean([abs(e) for e in self.error_history])
        error_std = np.std(self.error_history)
        
        # Performanz-Metrik (kleiner ist besser)
        performance = current_error + 0.5 * mean_error + 0.2 * error_std
        self.performance_history.append(performance)
        
        if len(self.performance_history) > 10:
            # Trend erkennen
            recent_performance = np.mean(list(self.performance_history)[-10:])
            older_performance = np.mean(list(self.performance_history)[:10])
            
            # Parameter anpassen basierend auf Performanz
            if recent_performance > older_performance * 1.1:  # Verschlechterung
                # Verstärkungen reduzieren
                self.kp *= (1 - self.adaptation_rate)
                self.ki *= (1 - self.adaptation_rate)
                self.kd *= (1 - self.adaptation_rate)
            elif recent_performance < older_performance * 0.9:  # Verbesserung
                # Verstärkungen erhöhen (aber vorsichtig)
                self.kp *= (1 + self.adaptation_rate * 0.5)
                self.ki *= (1 + self.adaptation_rate * 0.5)
                self.kd *= (1 + self.adaptation_rate * 0.5)
            
            # Parameter begrenzen
            self.kp = np.clip(self.kp, self.min_kp, self.max_kp)
            self.ki = np.clip(self.ki, self.min_ki, self.max_ki)
            self.kd = np.clip(self.kd, self.min_kd, self.max_kd)
    
    def set_setpoint(self, setpoint):
        """
        Setzt einen neuen Sollwert
        
        Args:
            setpoint: Neuer Sollwert (0-100%)
        """
        self.setpoint = np.clip(setpoint, 0, 100)
        
    def reset(self):
        """
        Setzt den Regler zurück
        """
        self.error_sum = 0
        self.last_error = 0
        self.last_input = 0
        self.error_history.clear()
        self.performance_history.clear()
        
    def get_parameters(self):
        """
        Gibt die aktuellen PID-Parameter zurück
        
        Returns:
            dict: Aktuelle Parameter
        """
        return {
            'kp': self.kp,
            'ki': self.ki,
            'kd': self.kd,
            'setpoint': self.setpoint
        }


class PIDController:
    """
    Einfacher PID-Regler ohne adaptive Parameter
    """
    
    def __init__(self, kp=1.0, ki=0.1, kd=0.05, setpoint=50.0):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.setpoint = setpoint
        self.integral = 0
        self.last_error = 0
        
    def compute(self, input_value, dt):
        """
        Berechnet den Ausgangswert
        
        Args:
            input_value: Istwert (0-100%)
            dt: Zeitschritt in Sekunden
            
        Returns:
            float: Stellgröße (0-100%)
        """
        error = self.setpoint - input_value
        
        # P-Anteil
        p_term = self.kp * error
        
        # I-Anteil
        self.integral += error * dt
        i_term = self.ki * self.integral
        
        # D-Anteil
        derivative = (error - self.last_error) / dt if dt > 0 else 0
        d_term = self.kd * derivative
        
        # Ausgang berechnen und begrenzen
        output = p_term + i_term + d_term
        output = np.clip(output, 0, 100)
        
        # Zustände speichern
        self.last_error = error
        
        return output


if __name__ == "__main__":

    sample_time = 0.02
    
    # Adaptiven PID-Regler erstellen
    pid = AdaptivePID(kp=10.0, ki=0.0, kd=0.0, setpoint=10.0, sample_time=sample_time)
    
    # Simulationsparameter
    sim_time = 60       # Sekunden
    dt = 0.01          # Zeitschritt
    steps = int(sim_time / dt)
    
    # Arrays für Daten
    time_array = np.arange(0, sim_time, dt)
    setpoint_array = np.zeros(steps)
    input_array = np.zeros(steps)
    output_array = np.zeros(steps)
    kp_array = np.zeros(steps)
    ki_array = np.zeros(steps)
    kd_array = np.zeros(steps)
    
    # Initialwert
    current_value = 1.0
    
    # Simulation mit Störungen
    for i in range(steps):

        t = i * dt
        
        # Sollwert-Änderungen
        #if 5 < t < 10:
        #    pid.set_setpoint(80)
        #elif 15 < t < 20:
        #    pid.set_setpoint(40)
        #elif t > 25:
        #    pid.set_setpoint(60)
        #else:
        #    pid.set_setpoint(50)
            
        setpoint_array[i] = pid.setpoint
        
        # PID berechnen
        output = pid.compute(current_value)

        if output is not None:

            output_array[i] = output
            
            # Prozesssimulation (einfaches PT1-Verhalten)
            current_value = current_value + (output - current_value) * 0.1 * dt * 10
            
            # Störungen
            #if 8 < t < 8.5:
            #    current_value += 15  # Störung nach oben
            #if 18 < t < 18.3:
            #    current_value -= 20  # Störung nach unten
                
            current_value = np.clip(current_value, 0, 100)
            
            # Parameter anpassen (alle 10 Schritte)
            #if i % 10 == 0:
            #    pid.adapt_parameters()
        
        input_array[i] = current_value
        kp_array[i] = pid.kp
        ki_array[i] = pid.ki
        kd_array[i] = pid.kd

    error = setpoint_array - input_array
    
    PLOT = True

    if PLOT:

        # Ergebnisse plotten
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(3, 1, figsize=(12, 10))
        
        # Plot 1: Regelung
        axes[0].plot(time_array, setpoint_array, 'r--', label='Sollwert', linewidth=2)
        axes[0].plot(time_array, input_array, 'b-', label='Istwert', linewidth=1)
        axes[0].plot(time_array, output_array, 'g-', label='Stellgröße', linewidth=1)
        axes[0].set_ylabel('Wert [%]')
        axes[0].set_title('Adaptive PID-Regelung')
        axes[0].legend()
        axes[0].grid(True)
        #axes[0].set_ylim(0, 100)
        
        # Plot 2: Adaptierte Parameter
        axes[1].plot(time_array, kp_array, 'r-', label='Kp', linewidth=1)
        axes[1].plot(time_array, ki_array, 'b-', label='Ki', linewidth=1)
        axes[1].plot(time_array, kd_array, 'g-', label='Kd', linewidth=1)
        axes[1].set_ylabel('Verstärkung')
        axes[1].set_title('Adaptierte PID-Parameter')
        axes[1].legend()
        axes[1].grid(True)
        
        # Plot 3: Regelabweichung        
        axes[2].plot(time_array, error, 'k-', label='Regelabweichung', linewidth=1)
        axes[2].set_xlabel('Zeit [s]')
        axes[2].set_ylabel('Abweichung [%]')
        axes[2].set_title('Regelabweichung')
        axes[2].legend()
        axes[2].grid(True)
        
        plt.tight_layout()
        plt.show()
    
    # Zusammenfassung
    print("Simulation abgeschlossen!")
    print(f"Finale PID-Parameter: Kp={pid.kp:.3f}, Ki={pid.ki:.3f}, Kd={pid.kd:.3f}")
    print(f"Mittlere Regelabweichung: {np.mean(np.abs(error)):.3f}%")