#!/usr/bin/python3

import time

import rospy
import roslibpy
from autoware_msgs.msg import VehicleCmd
from sensor_msgs.msg import Joy

class RosBridgeConnector():
    def __init__(self):
        rospy.init_node('yamaha_rosbridge_client')
        # ROS Subscriber
        self.vehicle_cmd_subscriber = rospy.Subscriber('/vehicle_cmd', VehicleCmd, self.vehicle_cmd_callback, queue_size=1)
        self.joy_subscriber = rospy.Subscriber('/joy', Joy, self.joy_callback, queue_size=1)

        # ROSBridge Websocket Instantiation
        self.ws_host = rospy.get_param("~host", "127.0.0.1")
        self.ws_port = rospy.get_param("~port", "9090")
        self.ws_reconnection_period = rospy.get_param("~reconnection_period", 1)
        self.ws_client = roslibpy.Ros(host=self.ws_host, port=self.ws_port)
        # ROSBridge Websocket Publisher
        self.ws_vehicle_cmd_publisher = roslibpy.Topic(self.ws_client, "/nav_vel", "geometry_msgs/TwistStamped")
        self.ws_joy_publisher = roslibpy.Topic(self.ws_client, "/joy", "sensor_msgs/Joy")
        
        # Private for checking reconnection
        self._timestamp = 0

    def connect(self):
        try:
            self.ws_client.run()
            rospy.loginfo("Server connected")
        except Exception as e:
            rospy.logerr("Unable to connect to server! %s", e)

    def advertise_topics(self):
        try:
            if self.ws_client.is_connected:
                self.ws_vehicle_cmd_publisher.advertise()
                self.ws_joy_publisher.advertise()
                rospy.loginfo("Topics are successfully advertised")
            else:
                rospy.logerr("Unable to advertise the topic sinces client is not connected to the server yet")
        except Exception as e:
            rospy.logerr("Unable to advertise the topic! %s", e)

    def unadvertise_topics(self):
        try:
            if self.ws_client.is_connected:
                self.ws_vehicle_cmd_publisher.unadvertise()
                self.ws_joy_publisher.unadvertise()
                rospy.loginfo("Topics are successfully unadvertised")
            else:
                rospy.logerr("Unable to unadvertise the topics since client is not connected to the server yet")
        except Exception as e:
            rospy.logerr("Unable to unadvertise the topic! %s", e)
    
    def terminate(self):
        try:    
            self.ws_client.terminate()
            rospy.loginfo("Server connection terminated")
        except Exception as e:
            rospy.logerr("Unable to terminate connection with server! %s", e)

    def vehicle_cmd_callback(self, data):
        try:
            if self.ws_client.is_connected:
                vehicle_cmd_json = roslibpy.Message(
                    {
                        "header": {
                            "stamp": {
                                "secs": data.header.stamp.secs,
                                "nsecs": data.header.stamp.nsecs
                            },
                            "frame_id": data.header.frame_id
                        },
                        "twist": {
                            "linear": {
                                "x": data.twist_cmd.twist.linear.x,
                                "y": data.twist_cmd.twist.linear.y,
                                "z": data.twist_cmd.twist.linear.z
                            },
                            "angular": {
                                "x": data.twist_cmd.twist.angular.x,
                                "y": data.twist_cmd.twist.angular.y,
                                "z": data.twist_cmd.twist.angular.z
                            }
                        }
                    }
                )
                self.ws_vehicle_cmd_publisher.publish(vehicle_cmd_json)
            else:
                rospy.logerr("Server is not connected")
        except Exception as e:
            rospy.logerr("Unable to publish message! %s", e)

    def joy_callback(self, data):
        try:
            if self.ws_client.is_connected:
                joy_json = roslibpy.Message(
                    {
                        "header": {
                            "stamp": {
                                "secs": data.header.stamp.secs,
                                "nsecs": data.header.stamp.nsecs
                            },
                            "frame_id": data.header.frame_id
                        },
                        "axes": data.axes,
                        "buttons": data.buttons
                    }
                )
                self.ws_joy_publisher.publish(joy_json)
            else:
                rospy.logerr("Server is not connected")
        except Exception as e:
            rospy.logerr("Unable to publish message! %s", e)

    def handle_reconnection(self):
        if time.time() - self._timestamp > self.ws_reconnection_period: 
            if not self.ws_client.is_connected:
                rospy.logwarn("Unable to connect to the server! Retrying...")
                self.connect()
                self.advertise_topics()
            self._timestamp = time.time()

def main():
    init = RosBridgeConnector()
    init.connect()
    init.advertise_topics()
    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        init.handle_reconnection()
        rate.sleep()
    init.unadvertise_topics()
    init.terminate()
    
if __name__ == '__main__':
    main()