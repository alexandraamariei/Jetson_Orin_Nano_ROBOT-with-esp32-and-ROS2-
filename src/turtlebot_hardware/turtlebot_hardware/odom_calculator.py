#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
import math

from std_msgs.msg import Int32
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

class OdomCalculator(Node):
    def __init__(self):
        super().__init__('odom_calculator')

        # === PARAMETRI FIZICI AI ROBOTULUI TĂU ===
        
        self.wheel_radius = 0.026  # Raza roții în metri 
        self.wheel_track = 0.14    # Distanța dintre roți 
        self.ticks_per_rev = 374.2 # Câți pași scoate encoderul la o rotație completă a roții

        # Calculăm distanța parcursă de roată la un singur pas
        # Formula: (2 * Pi * Raza) /nr_pasi
        self.dist_per_tick = (2.0 * math.pi * self.wheel_radius) / self.ticks_per_rev

        # === VARIABILE DE STARE ===
        self.x = 0.0      # Poziția pe X în metri
        self.y = 0.0      # Poziția pe Y în metri
        self.theta = 0.0  # Rotația (unghiul) în radiani

        self.last_left_ticks = 0
        self.last_right_ticks = 0
        self.first_read = True

        self.last_time = self.get_clock().now()

        # === ABONAMENTE (Ascultăm ESP32-ul) ===
        self.sub_left = self.create_subscription(Int32, '/left_encoder_ticks', self.left_tick_cb, 10)
        self.sub_right = self.create_subscription(Int32, '/right_encoder_ticks', self.right_tick_cb, 10)

        self.current_left_ticks = 0
        self.current_right_ticks = 0

        # === PUBLICARE (Trimitem către RViz2) ===
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # Calculăm odometria de 20 de ori pe secundă
        self.timer = self.create_timer(0.05, self.update_odom)
        self.get_logger().info("Odom Calculator a pornit! Astept date de la ESP32...")

    def left_tick_cb(self, msg):
        self.current_left_ticks = msg.data

    def right_tick_cb(self, msg):
        self.current_right_ticks = msg.data

    def update_odom(self):
        # Așteptăm până primim primele date de la ESP32 ca să nu avem erori
        if self.first_read:
            self.last_left_ticks = self.current_left_ticks
            self.last_right_ticks = self.current_right_ticks
            self.first_read = False
            return

        current_time = self.get_clock().now()
        dt = (current_time - self.last_time).nanoseconds / 1e9 # secunde

        # 1. Câți pași a făcut fiecare roată de la ultima citire
        delta_left_ticks = self.current_left_ticks - self.last_left_ticks
        delta_right_ticks = self.current_right_ticks - self.last_right_ticks

        # Actualizăm ultima valoare(cea anterioara)
        self.last_left_ticks = self.current_left_ticks
        self.last_right_ticks = self.current_right_ticks
        self.last_time = current_time

        # 2. Câți metri a parcurs fiecare roată
        dist_left = delta_left_ticks * self.dist_per_tick
        dist_right = delta_right_ticks * self.dist_per_tick

        # 3. CINEMATICA ROBOTULUI
        # Distanța parcursă de centrul robotului
        dist_center = (dist_left + dist_right) / 2.0
        # Rotația robotului
        delta_theta = (dist_right - dist_left) / self.wheel_track

        # 4. Actualizarea coordonatelor globale (X, Y, Theta)
        self.theta += delta_theta
        self.x += dist_center * math.cos(self.theta)
        self.y += dist_center * math.sin(self.theta)

        # Vitezele (pt nav2)
        v = dist_center / dt if dt > 0 else 0.0
        w = delta_theta / dt if dt > 0 else 0.0

        # Transformăm unghiul Theta într-un format cerut de ROS 2 
        q_x, q_y, q_z, q_w = 0.0, 0.0, math.sin(self.theta / 2.0), math.cos(self.theta / 2.0)

        # 5. Publicăm mesajul de Odometrie (/odom)
        odom = Odometry()
        odom.header.stamp = current_time.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id = 'base_link'
        
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.position.z = 0.0
        odom.pose.pose.orientation.x = q_x
        odom.pose.pose.orientation.y = q_y
        odom.pose.pose.orientation.z = q_z
        odom.pose.pose.orientation.w = q_w
        
        odom.twist.twist.linear.x = v
        odom.twist.twist.angular.z = w
        self.odom_pub.publish(odom)

        # 6. Publicăm TF-ul (Transformarea 3D pentru RViz)
        t = TransformStamped()
        t.header.stamp = current_time.to_msg()
        t.header.frame_id = 'odom'
        t.child_frame_id = 'base_link'
        t.transform.translation.x = self.x
        t.transform.translation.y = self.y
        t.transform.translation.z = 0.0
        t.transform.rotation.x = q_x
        t.transform.rotation.y = q_y
        t.transform.rotation.z = q_z
        t.transform.rotation.w = q_w
        self.tf_broadcaster.sendTransform(t)

def main(args=None):
    rclpy.init(args=args)
    node = OdomCalculator()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()