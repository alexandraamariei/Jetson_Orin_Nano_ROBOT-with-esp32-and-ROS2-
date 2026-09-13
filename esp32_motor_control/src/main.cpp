#include <Arduino.h>
#include <micro_ros_platformio.h>
#include <rcl/rcl.h>
#include <rcl/error_handling.h>
#include <rclc/rclc.h>
#include <rclc/executor.h>
#include <geometry_msgs/msg/twist.h>
#include <std_msgs/msg/int32.h>
#include <rmw_microros/rmw_microros.h>
// ==== SETĂRI PINI MOTOR STÂNGA (Motor 1) ====
#define IN1 5
#define IN2 18
#define ENC1_A 13
#define ENC1_B 4

// ==== SETĂRI PINI MOTOR DREAPTA (Motor 2) ====
#define IN3 26
#define IN4 32
#define ENC2_A 22
#define ENC2_B 23
unsigned long last_ping_time = 0;
// Contoare pentru encodere
volatile long leftEncoderCount = 0;
volatile long rightEncoderCount = 0;

// Variabilele pentru micro-ROS
rcl_subscription_t subscriber;
rcl_publisher_t left_publisher;
rcl_publisher_t right_publisher;
geometry_msgs__msg__Twist msg;
std_msgs__msg__Int32 left_pub_msg;
std_msgs__msg__Int32 right_pub_msg;

rclc_executor_t executor;
rclc_support_t support;
rcl_allocator_t allocator;
rcl_node_t node;

unsigned long last_time = 0;

// Distanța dintre roți în metri 
float WHEEL_TRACK = 0.15; 

// Întreruperi pentru encodere
void IRAM_ATTR readLeftEncoder() {
  if (digitalRead(ENC1_B) == HIGH) {
    leftEncoderCount++;
  } else {
    leftEncoderCount--;
  }
}

void IRAM_ATTR readRightEncoder() {
  if (digitalRead(ENC2_B) == HIGH) {
    rightEncoderCount++;
  } else {
    rightEncoderCount--;
  }
}

// Funcție ajutătoare pentru a comanda un motor individual (PWM + Direcție)
void moveMotor(int pinA, int pinB, float speed) {
  int pwm = abs(speed) * 255;
  if (pwm > 255) pwm = 255;

  if (speed > 0.05) {
    analogWrite(pinA, pwm);
    analogWrite(pinB, 0);
  } else if (speed < -0.05) {
    analogWrite(pinA, 0);
    analogWrite(pinB, pwm);
  } else {
    analogWrite(pinA, 0);
    analogWrite(pinB, 0);
  }
}

// Callback-ul care primește comanda de la Jetson și calculează cinematică diferențială
void cmd_vel_callback(const void * msgin) {
  const geometry_msgs__msg__Twist * twist_msg = (const geometry_msgs__msg__Twist *)msgin;
  
  float linear = twist_msg->linear.x;
  float angular = twist_msg->angular.z;

  // Cinematică diferențială: viteză roată stânga și dreapta
  float left_speed  = linear - (angular * WHEEL_TRACK / 2.0);
  float right_speed = linear + (angular * WHEEL_TRACK / 2.0);

  // Aplicăm vitezele pe cele două motoare
  moveMotor(IN1, IN2, left_speed);
  moveMotor(IN3, IN4, right_speed);
}

void setup() {
  // 1. OPRIM MOTOARELE FORȚAT LA PORNIRE
  pinMode(IN1, OUTPUT); analogWrite(IN1, 0);
  pinMode(IN2, OUTPUT); analogWrite(IN2, 0);
  pinMode(IN3, OUTPUT); analogWrite(IN3, 0);
  pinMode(IN4, OUTPUT); analogWrite(IN4, 0);

  // 2. Pornim comunicarea serială
  Serial.begin(115200);
  set_microros_serial_transports(Serial);
  
  // 3. Așteaptă la infinit până când Jetson-ul deschide portul
  // 3. AUTO-RESET LA PORNIRE (apăsăm butonul din cod)
  int retries = 0;
  while (rmw_uros_ping_agent(100, 1) != RMW_RET_OK) {
    delay(100);
    retries++;
    if (retries > 50) { 
      // Dacă au trecut 5 secunde și Jetson-ul nu răspunde, dăm restart!
      ESP.restart(); 
    }
  }
  delay(1000);

  // 4. Configurare pini encodere
  pinMode(ENC1_A, INPUT_PULLUP);
  pinMode(ENC1_B, INPUT_PULLUP);
  pinMode(ENC2_A, INPUT_PULLUP);
  pinMode(ENC2_B, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(ENC1_A), readLeftEncoder, RISING);
  attachInterrupt(digitalPinToInterrupt(ENC2_A), readRightEncoder, RISING);

  // 5. Inițializare micro-ROS
  allocator = rcl_get_default_allocator();
  rclc_support_init(&support, 0, NULL, &allocator);
  rclc_node_init_default(&node, "esp32_motor_controller", "", &support);

  // 6. Abonament pentru /cmd_vel
  rclc_subscription_init_default(
    &subscriber,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(geometry_msgs, msg, Twist),
    "/cmd_vel"
  );

  // 7. Publisher-e pentru encodere (stânga și dreapta separat)
  rclc_publisher_init_default(
    &left_publisher,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
    "/left_encoder_ticks"
  );

  rclc_publisher_init_default(
    &right_publisher,
    &node,
    ROSIDL_GET_MSG_TYPE_SUPPORT(std_msgs, msg, Int32),
    "/right_encoder_ticks"
  );

  rclc_executor_init(&executor, &support.context, 1, &allocator);
  rclc_executor_add_subscription(&executor, &subscriber, &msg, &cmd_vel_callback, ON_NEW_DATA);
}

void loop() {
  // Verificăm dacă Jetson-ul mai e acolo o dată la 2 secunde
  if (millis() - last_ping_time > 2000) {
    last_ping_time = millis();
    if (rmw_uros_ping_agent(10, 1) != RMW_RET_OK) {
      // S-a tăiat conexiunea! Dăm restart ca să o luăm de la zero.
      ESP.restart();
    }
  }

 
  
  rclc_executor_spin_some(&executor, RCL_MS_TO_NS(10));
}
