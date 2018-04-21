// Arduino timer CTC interrupt example
// www.engblaze.com
 
// avr-libc library includes
#include <avr/io.h>
#include <avr/interrupt.h>
 
#define LEDPIN 2

unsigned long timer = 0;
String string_me = "serial ";
void setup()
{
  Serial.begin(57600);
    pinMode(LEDPIN, OUTPUT);
 
    // initialize Timer1
    cli();          // disable global interrupts
    TCCR1A = 0;     // set entire TCCR1A register to 0
    TCCR1B = 0;     // same for TCCR1B
 
    // set compare match register to desired timer count:
    //OCR1A = 15.625; 1Khz , 1
    //OCR1A = 7.8; 2Khz, 0.5
    //OCR1A = 3.9; //4KHz, 0.25
    //OCR1A = 3.125; //5KHz, 0.20 
    OCR1A = 1.5625; //10KHz, 0.1
    // turn on CTC mode:
    TCCR1B |= (1 << WGM12);
    // Set CS10 and CS12 bits for 1024 prescaler:
    TCCR1B |= (1 << CS10);
    TCCR1B |= (1 << CS12);
    // enable timer compare interrupt:
    TIMSK1 |= (1 << OCIE1A);
    // enable global interrupts:
    sei();
}
 
void loop()
{
  
    // do some crazy stuff while my LED keeps blinking
}
 
ISR(TIMER1_COMPA_vect)
{
    //int sensorValue = analogRead(A0);
    
    //String time_res = "Time: ";
    //timer = 0;
    //unsigned long timer2 = micros();
    //Serial.println(timer2);
    //unsigned long timerF = timer2 - timer;
    //int var = analogRead(A0);
    //Serial.println(timer2 - timer);
    //Serial.println(1);
    Serial.println(analogRead(A0));
    
    //timer = timer2;
    //Serial.print("Serial:");
    //Serial.println(timer2);
    
    //digitalWrite(LEDPIN, !digitalRead(LEDPIN));
    
}
