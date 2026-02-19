let ss = [
    'TP1_ENABLE','TP1_CONTINOUS','TP1_POS','TP1_NEG','TP1_INPUT',
    'TP2_ENABLE','TP2_CONTINOUS','TP2_POS','TP2_NEG','TP2_INPUT'
];

let cc = ['ENABLE', 'CONTINOUS', 'POS', 'NEG', 'INPUT'];
cc.forEach(function(c, i) {
    let enable = ss.filter(s => s.includes(c)).length > 0;
    console.log(enable);
});
