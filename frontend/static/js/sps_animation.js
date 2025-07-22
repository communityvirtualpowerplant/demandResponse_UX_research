let endpoint = '/api/data?file=now'
getData(endpoint)
setInterval(getData,60000);

let myData

let parentElement = 'statusCanvasContainer'

function setup() {

  cW = getCanvasWidth()
  cH = getCanvasHeight(cW) //update if this needs to be dynamic

  let canvas = createCanvas(cW, cH);

  canvas.parent(parentElement); // Attach to the specific div 
}

function getCanvasWidth(){
  const pE = document.getElementById(parentElement);

  // console.log(pE.clientWidth)
  // console.log(pE.parentElement.clientWidth)
  if (pE.clientWidth == 0){
    return pE.parentElement.clientWidth * .45
  } else {
    return min(pE.clientWidth, (768*.9))
  }
}

function getCanvasHeight(w){
  return 400 * (w / 700)
}


function windowResized() {
  cW = getCanvasWidth()
  cH = getCanvasHeight(cW) //update if this needs to be dynamic

  resizeCanvas(cW, cH);
  //updateData(myData); // Optional: redraw immediately on resize
  drawSystem(myData);
}

function getData(url){
  fetch(url)
    .then(response => {
      if (!response.ok) {
        throw new Error('Network response was not OK');
      }
      return response.text(); // or response.text() if it's plain text
    })
    .then(data => {
      const safeJSON = data.replace(/\bNaN\b/g, 'null');
      data = JSON.parse(safeJSON);
      //console.log('Data received:', data);
      myData = data
      //updateData(myData)
      drawSystem(myData);
    })
    .catch(error => {
      console.error('There was a problem with the fetch:', error);
    });
}


function drawSystem(data) {
  let cWscaler = cW/700
  let cHscaler = cH/500

  background(220);

  let centerH = height/2;
  let centerW = width/2;
  
  textSize(max(14* cWscaler,11));
  textAlign(CENTER);
  fill(0);
  stroke(0);
  
  // everything is aligned around 5 points on the X-axis
  let xOne = width * .15
  let xTwo = (width * .15) + (width * .15)  
  let xThree = width * .5
  let xFour = (width * .7)  
  let xFive = width * .85

  let batWidth = 100 * cWscaler
  let batCenterX = xThree
  let batHeight = 75 * cHscaler
  let batCenterY = height/2-batHeight*1.25;
  let batH = 160
  let circleDiam = 26 * cWscaler
  let circleDiamCenter = 20 * cWscaler
  let pvH = batCenterY-(batHeight/3)

  let relay1H = batCenterY
  let transferSwitch = 50 * cWscaler
  let smCenterY = height/2+batHeight*1.25;

  //let batP=data['battery']*0.01
  // let gridV = data['grid vac']
  // let posOne =data['sensor 1 wac']
  // let posTwo = data['sensor 2 wac']
  // let posThree = data['sensor 3 wac']
  // let posFour = data['sensor 4 wdc']

  let batP=data['powerstation_percentage']*0.01
  let gridV = data['relay1_voltage']
  let posOne =data['relay1_power']
  let posTwo = data['relay2_power']
  let posThree = data['relay3_power']
  let posFour = data['powerstation_inputWDC']

  let loadW
  if (posOne > 0){
    loadW = posOne;
  } else if (posThree > 0){ 
    loadW = posThree;
  } else {
    loadW = 0
  }

  // Draw wires and connections
  let wireBool;
  
  if (posOne > 0){
    wireBool = true;
  } else{
    wireBool = false;
  }
  drawWire([[xOne, centerH, xTwo, centerH],[xTwo, centerH, xTwo, smCenterY],[xTwo, smCenterY, xFour, smCenterY],[xFour, smCenterY, xFour, centerH]],wireBool);// Grid to transfer switch

  if (posTwo > 0){
    wireBool = true;
  } else{
    wireBool = false;
  }
  drawWire([[xOne, centerH, xTwo, centerH],[xTwo, centerH, xTwo, batCenterY],[xTwo, batCenterY, batCenterX-batWidth/2, batCenterY]],wireBool); // Grid to battery
 
  if (posThree > 0){
    wireBool = true;
  } else{
    wireBool = false;
  }
  drawWire([[batCenterX+batWidth/2, batCenterY, xFour, batCenterY],[xFour, batCenterY, xFour, centerH]],wireBool); // Battery to transfer switch
  
  if (posOne > 0 || posThree > 0 ){
    wireBool = true;
  } else{
    wireBool = false;
  }
  drawWire([[xFour, centerH, xFive, centerH]],wireBool); // transfer switch to Load

  if (posFour > 0){
    wireBool = true;
  } else{
    wireBool = false;
  }
  drawWire([[xOne, pvH, batCenterX-batWidth/2, pvH]],wireBool); // PV to battery
  

  push()
    // Draw grid power source
    // Draw PV source
    if(posOne > 0 || posTwo > 0 || gridV > 0){
      fill(200, 150, 255)
      noStroke()
      circle(xOne, centerH, circleDiam); // grid indicator
    }
    strokeWeight(2);
    fill(150);
    stroke(0);
    circle(xOne, centerH, circleDiamCenter); // Grid Source Box
    fill(0);
    underText("Grid\n"+ gridV +" VAC", xOne, centerH+(20*cWscaler));

    // Draw PV source
    if(posFour > 0){
      fill(200, 150, 255)
      noStroke()
      circle(xOne, pvH, circleDiam); // PV Source Box
    }
    fill(150);
    strokeWeight(2);
    stroke(0);
    circle(xOne, pvH, circleDiamCenter); // PV Source Box
    fill(0);
    underText("PV", xOne, pvH+(15*cWscaler));
    
    // Draw load (maybe also highlight load if gridV is available and posOne is open)
    if(posOne > 0 || posThree > 0){
      fill(200, 150, 255)
      noStroke();
      circle(xFive, centerH, circleDiam); // load indicator
    }
    strokeWeight(2);
    fill(150);
    stroke(0);
    circle(xFive, centerH, circleDiamCenter); // Grid Source Box
    fill(0);
    underText("Load\n" +loadW +" Watts", xFive, centerH+20);
  pop();
 
  // Draw battery system
  push()
    rectMode(CORNER);
    fill(255)
    noStroke()
    rect(batCenterX-batWidth/2, batCenterY-batHeight/2+batHeight-(batHeight*batP), batWidth, batHeight*batP); // Battery Box
    stroke(0)
    noFill()
    rect(batCenterX-batWidth/2, batCenterY-batHeight/2, batWidth, batHeight); // Battery Box Outline
    underText("Battery\n" + batP*100 +"%", batCenterX, batCenterY+batHeight/2+10);
  pop()
  
   // Draw Smart Relay 1
  rectMode(CENTER);
  fill(255)
  rect(xTwo, batCenterY, 10,10); // Battery Box
  leftText("P2: " + posTwo +"W", xTwo, batCenterY);
  fill(200)
  triangle(xTwo-5, batCenterY+5, xTwo, batCenterY-5, xTwo+5, batCenterY+5);

  // Draw Smart Relay 2
  rectMode(CENTER);
  fill(255)
  rect(xTwo, smCenterY, 10,10); // Battery Box
  leftText("P1: " + posOne + "W", xTwo, smCenterY);
  fill(200)
  triangle(xTwo-5, smCenterY+5, xTwo, smCenterY-5, xTwo + 5, smCenterY+5);

  // Draw Smart Relay 3
  rectMode(CENTER);
  fill(255)
  rect(xFour, batCenterY, 10,10); // Battery Box
  leftText("P3: " + posThree+"W", xFour, batCenterY-30);

  // Draw Sensor 4
  rectMode(CENTER);
  fill(255)
  rect(xTwo, pvH, 10,10); // Box
  leftText("P4: " + posFour+"W", xTwo, pvH-30);

  // Draw Transfer Switch
  push()
    rectMode(CENTER);
    stroke(0)
    fill(150)
    rect(xFour, centerH, transferSwitch,transferSwitch); // Battery Box
    noFill()
    let angleS = 0;
    let angleE = HALF_PI;
    if (posOne == 0 && posThree > 0){ 
      angleE = 0
      angleS = PI+HALF_PI
    }
    tsRad = transferSwitch* .8
    if (posOne > 0 || posThree > 0){ 
      stroke(200, 150, 255);
      strokeWeight(6);
      arc(xFour, centerH, tsRad, tsRad, angleS,angleE);
    }
    stroke(0)
    strokeWeight(2);
    arc(xFour, centerH, tsRad, tsRad, angleS,angleE);
    leftText("Transfer\n Switch", xFour- 5, centerH + 15);
  pop()

  // textAlign(CENTER,CENTER)
  // fill(0) 
  // noStroke()
  // textSize(20)
  // text("Demand Response Behind-The-Meter (BTM) System", centerW, 50);
  
    drawKey()
}

function drawKey(){
  push()
    textAlign(CENTER,CENTER)
    //textSize(14);

    rectMode(CENTER);
    stroke(0)
    fill(255)
    rect(20, height-20, 10,10);
    rect(150, height-20, 10,10);
    fill(200)
    triangle(15, height-15, 20, height-25, 25, height-15);

    drawWire([[220,height-20, 250,height-20]],false)

    drawWire([[305,height-20, 335,height-20]],true)

    noStroke(0)
    fill(0)
    textAlign(LEFT)
    text("Relay & Sensor", 30, height-20);
    text("Sensor", 160, height- 20);
    text("Dead", 255, height-20)
    text("Live", 340, height-20)
  pop()
}

function underText(t,x,y){
  push()
    noStroke();
    textAlign(CENTER, CENTER);
    fill(0);
    text(t, x,y+10);
    fill(150);
  pop()
}

function leftText(t,x,y){
  push()
    noStroke();
    textAlign(RIGHT,TOP);
    fill(0);
    text(t, x,y+10);
    fill(150);
  pop()
}

function drawWire(a,state){
  push();
    if (state==true){
      stroke(200, 150, 255);
      strokeWeight(6);
      for (let w in a){
        c = a[w]
        line(c[0],c[1],c[2],c[3]);
      }
    }
  
    strokeWeight(2);
    stroke(0);
    for (let w in a){
        c = a[w]
        line(c[0],c[1],c[2],c[3]);
      }
  pop()
}