
let fxl = {

    laserUnit: {
        mba: 5,         // cm Messbereichsanfang
        mb: 10,         // cm Messbereich
        mbe: 15,        // cm Messbereichsende
        ampRange: 16
    },

    driveUnit: {
        mode: 'AM8111',                                             // AM8111, ED1F
        gearBoxGearRatio: 1000.0,
        spindlePitch: 5.0,
        timingBeltTransmissionGearRatio: 2.0,
        motorIncrementPositions: 1048576,                           // AM8111: 1048576; ED1F: 8388608
        cylinderDiameter: 15.0,
        cylinderVolume: 10.0,
        cylinderArea: 176.7146                                      // cm^2 cylinderDiameter ** 2 * Math.PI / 4.
    },

    position: {

        limit: {
            max: 13.11,   // cm top
            min:  8.13,   // cm bottom
            dev: 0.050
        },

        unit: "cm",
        digits: 3,

        valid: function (value, direction) {
            if (direction == -1 && value < this.limit.min - this.limit.dev)
                return false;
            if (direction == 1 && value > this.limit.max + this.limit.dev)
                return false;
            return true;
        }
    },

    volume: {
        limit: {
            min: 0.0,   // top (1ml)
            max: 9.0    // bottom (1ml + 7ml) 
        },
        unit: "ml",
        digits: 3,
        valid: function (value) {
            return value >= this.limit.min && value <= this.limit.max;
        }
    },

    amp2cm: function (value) {
        return this.laserUnit.mba + this.laserUnit.mb * value / this.laserUnit.ampRange;
    },

    amp2ml: function (value) {
        return this.volume.limit.min + (this.position.limit.max - this.amp2cm(value)) * this.driveUnit.cylinderArea / 100.0;
    },

    incs2mulmin: function (value) {
        // mm/r
        let transmission = this.driveUnit.spindlePitch / (this.driveUnit.timingBeltTransmissionGearRatio * this.driveUnit.gearBoxGearRatio);
        // mm³/r ~ µl/r
        let injectionRateRotation = transmission * this.driveUnit.cylinderArea;
        // µl/inc
        let injectionRateIncrement = injectionRateRotation / this.driveUnit.motorIncrementPositions;
        return value * injectionRateIncrement * 60;
    },

    incs2nalmin: function (value) {
        return this.incs2mulmin(value) * 1000;
    },

    mulmin2incs: function (value) {
        // mm/r
        let transmission = this.driveUnit.spindlePitch / (this.driveUnit.timingBeltTransmissionGearRatio * this.driveUnit.gearBoxGearRatio);
        // µl/r
        let injectionRateRotation = transmission * this.driveUnit.cylinderArea;
        // µl/inc
        let injectionRateIncrement = injectionRateRotation / this.driveUnit.motorIncrementPositions;
        // µl/min
        return value / (injectionRateIncrement * 60);
    },

    nalmin2incs: function (value) {
        return this.mulmin2incs( value / 1000.0);
    }

}

console.log( fxl.mulmin2incs(2650) );

console.log( fxl.incs2mulmin(24185993) );