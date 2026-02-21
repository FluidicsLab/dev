
let hot = {    

    "driveUnit": {
        gearBoxGearRatio: 1000.,
        spindlePitch: 5.,
        timingBeltTransmissionGearRatio: 2.,
        motorIncrementPositions: 8388608,
        cylinderDiameter: 15.,
        cylinderVolume: 10.,
    },

    "velocity2volume": function(value) {
        // inc/s; 838_860_800 max
        let cylinderArea = (this.driveUnit.cylinderDiameter ** 2.) * Math.PI / 4.;
        // mm/r
        let transmission = this.driveUnit.spindlePitch / (this.driveUnit.timingBeltTransmissionGearRatio * this.driveUnit.gearBoxGearRatio);
        // µl/r
        let injectionRateRotation = transmission * cylinderArea;
        // µl/inc
        let injectionRateIncrement = injectionRateRotation / this.driveUnit.motorIncrementPositions;
        return Math.round(1000 * value * injectionRateIncrement * 60) / 1000;
    },
    
    "volume2velocity": function (value) {
        // inc/s; 838_860_800 max
        let cylinderArea = (this.driveUnit.cylinderDiameter ** 2.) * Math.PI / 4.;
        // mm/r
        let transmission = this.driveUnit.spindlePitch / (this.driveUnit.timingBeltTransmissionGearRatio * this.driveUnit.gearBoxGearRatio);
        // µl/r
        let injectionRateRotation = transmission * cylinderArea;
        // µl/inc
        let injectionRateIncrement = injectionRateRotation / this.driveUnit.motorIncrementPositions;
        return value / (injectionRateIncrement * 60);
    }

};


console.log(hot.volume2velocity(2000));