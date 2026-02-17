
class ProfilePosition {

    static value(value, range) {
        return value < 0 ? Math.pow(2, range) - 1 + value : value;
    }

    static merge(value, bits, range=32) {
        return this.value(parseInt(
            value[0].toString(2).padStart(bits,'0') + 
            value[1].toString(2).padStart(range-bits,'0'),2)
        );
    }

    static split(value, bits, range=32) {
        value = value.toString(2).padStart(range, '0');
        return [parseInt(value.slice(0,bits),2), parseInt(value.slice(bits),2)];
    }

}

let bits = 16;

let val = [17001,500];
let pos = ProfilePosition.merge(val, bits);

val = ProfilePosition.split(pos, bits);

console.log(pos, val);