#! /usr/bin/python3

import time
import rospy
import roslibpy
from autoware_msgs.msg import VehicleCmd
from sensor_msgs.msg import Joy
from std_msgs.msg import String, Float64
from nav_msgs.msg import Odometry
from diagnostic_msgs.msg import DiagnosticArray, DiagnosticStatus, KeyValue
from control_msgs.msg import JointTrajectoryControllerState
from std_srvs.srv import Trigger, TriggerResponse

class RosBridgeConnector():
    def __init__(self):
        rospy.init_node('yamaha_rosbridge_client')
        # ROS Subscriber
        self.vehicle_cmd_subscriber = rospy.Subscriber('/vehicle_cmd', VehicleCmd, self.vehicle_cmd_callback, queue_size=1)
        self.joy_subscriber = rospy.Subscriber('/joy', Joy, self.joy_callback, queue_size=1)
        self.brake_command_subscriber = rospy.Subscriber('/brake_cmd', Float64, self.brake_command_callback, queue_size=1)
        # ROS Publisher
        self.odometry_publisher = rospy.Publisher('/odometry', Odometry, queue_size=50)
        self.diagnostic_publisher = rospy.Publisher('/diagnostics', DiagnosticArray, queue_size=50)
        self.joint_trajectory_controller_state_publisher = rospy.Publisher('/joint_trajectory_controller_state', JointTrajectoryControllerState, queue_size=50)
        # ROS Service Server
        self.set_zero_service_server = rospy.Service('/set_zero_position', Trigger, self.set_zero_position_service_server)
        # ROSBridge Websocket Instantiation
        self.ws_host = rospy.get_param("~host", "127.0.0.1")
        self.ws_port = rospy.get_param("~port", "9090")
        self.ws_reconnection_period = rospy.get_param("~reconnection_period", 1)
        self.ws_client = roslibpy.Ros(host=self.ws_host, port=self.ws_port)
        # ROSBridge Websocket Subscriber
        self.talker_listener = roslibpy.Topic(self.ws_client, '/chatter', 'std_msgs/String')
        self.ws_odometry_subscriber = roslibpy.Topic(self.ws_client, '/bicycle_steering_controller/odometry', 'nav_msgs/Odometry')
        self.ws_diagnostic_subscriber = roslibpy.Topic(self.ws_client, '/diagnostics', 'diagnostic_msgs/DiagnosticArray')
        self.ws_joint_trajectory_controller_state_subscriber = roslibpy.Topic(self.ws_client, '/bicycle_steering_controller/controller_state', 'control_msgs/SteeringControllerStatus')
        # ROSBridge Websocket Publisher
        self.ws_vehicle_cmd_publisher = roslibpy.Topic(self.ws_client, "/nav_vel", "geometry_msgs/TwistStamped")
        self.ws_joy_publisher = roslibpy.Topic(self.ws_client, "/joy", "sensor_msgs/Joy")
        self.ws_brake_command_publisher = roslibpy.Topic(self.ws_client, "/brake_cmd", "std_msgs/Float64")
        # ROSBridge Websocket Service Request
        self.ws_service_request = roslibpy.Service(self.ws_client, '/set_zero_position', 'std_srvs/Trigger')
        # Private for checking reconnection
        self._timestamp = 0
        self._response_message = None
        self._success_status = None
        self._is_ws_service_server_correct_response = False

    def connect(self):
        try:
            self.ws_client.run()
            rospy.loginfo("Server connected")
        except Exception as e:
            rospy.logerr("Unable to connect to server! %s", e)

    def websocket_subscriber(self):
        try:
            if self.ws_client.is_connected:
                self.talker_listener.subscribe(self.talker_listener_callback)
                self.ws_odometry_subscriber.subscribe(self.ws_odometry_subscriber_callback)
                self.ws_diagnostic_subscriber.subscribe(self.ws_diagnostic_subscriber_callback)
                self.ws_joint_trajectory_controller_state_subscriber.subscribe(self.ws_joint_trajectory_controller_state_subscriber_callback)
                rospy.loginfo("Success for subscribe")
            else:
                rospy.logerr("Unable to subscribe the topic sinces client is not connected to the server yet")
        except Exception as e:
            rospy.logerr("Unable to subscribe from server! %s", e)  
    
    def advertise_topics(self):
        try:
            if self.ws_client.is_connected:
                self.ws_vehicle_cmd_publisher.advertise()
                self.ws_joy_publisher.advertise()
                self.ws_brake_command_publisher.advertise()
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

    def brake_command_callback(self, data):
        try:
            if self.ws_client.is_connected:
                brake_json = roslibpy.Message(
                    {
                        "data": data.data
                    }
                )
                self.ws_brake_command_publisher.publish(brake_json)
            else:
                rospy.logerr("Server is not connected")
        except Exception as e:
            rospy.logerr("Unable to publish message! %s", e)

    def talker_listener_callback(self, data):
        rospy.loginfo("Data: %s", data)
    
    def ws_odometry_subscriber_callback(self, data):
        odom = Odometry()
        odom.child_frame_id = data['child_frame_id']
        odom.pose.pose.position.x = data['pose']['pose']['position']['x']
        odom.pose.pose.position.y = data['pose']['pose']['position']['y']
        odom.pose.pose.position.z = data['pose']['pose']['position']['z']
        odom.pose.pose.orientation.x = data['pose']['pose']['orientation']['x']
        odom.pose.pose.orientation.y = data['pose']['pose']['orientation']['y']
        odom.pose.pose.orientation.z = data['pose']['pose']['orientation']['z']
        odom.pose.pose.orientation.w = data['pose']['pose']['orientation']['w']
        odom.pose.covariance = data['pose']['covariance']
        odom.twist.twist.linear.x = data['twist']['twist']['linear']['x']
        odom.twist.twist.linear.y = data['twist']['twist']['linear']['y']
        odom.twist.twist.linear.z = data['twist']['twist']['linear']['z']
        odom.twist.twist.angular.x = data['twist']['twist']['angular']['x']
        odom.twist.twist.angular.x = data['twist']['twist']['angular']['y']
        odom.twist.twist.angular.x = data['twist']['twist']['angular']['z']
        odom.twist.covariance = data['twist']['covariance']
        self.odometry_publisher.publish(odom)

    def ws_diagnostic_subscriber_callback(self, data):
        diag_array = DiagnosticArray()
        statuses = []
        for i in range(len(data["status"])):
            status = DiagnosticStatus()
            status.name = data["status"][i]["name"]
            status.level = data["status"][i]["level"]
            status.message = data["status"][i]["message"]
            status.hardware_id = data["status"][i]["hardware_id"]
            keys_values = []
            for j in range(len(data["status"][i]["values"])):
                key_value = KeyValue()
                key_value.key = data["status"][i]["values"][j]["key"]
                key_value.value = data["status"][i]["values"][j]["value"]
                keys_values.append(key_value)
            status.values.extend(keys_values)      
            statuses.append(status)
        diag_array.status.extend(statuses)
        self.diagnostic_publisher.publish(diag_array)

    def ws_joint_trajectory_controller_state_subscriber_callback(self, data):
        joint_state_msg = JointTrajectoryControllerState()
        joint_state_msg.joint_names = ["rear_wheel", "steering_axis"]
        joint_state_msg.actual.positions.insert(0, data['traction_wheels_position'][0])
        joint_state_msg.actual.velocities.insert(0, data['traction_wheels_velocity'][0])
        joint_state_msg.actual.positions.insert(1, data['steer_positions'][0])
        joint_state_msg.desired.velocities.insert(0, data['linear_velocity_command'][0])
        joint_state_msg.desired.positions.insert(0, 0.0)
        joint_state_msg.desired.positions.insert(1, data['steering_angle_command'][0])
        self.joint_trajectory_controller_state_publisher.publish(joint_state_msg)

    def set_zero_position_service_server(self, req):
        response = TriggerResponse()
        ws_request = roslibpy.ServiceRequest()
        self.ws_service_request.call(ws_request, self.ws_service_callback, self.ws_service_error_callback)
        time.sleep(2)
        if self._is_ws_service_server_correct_response:
            response.success = self._success_status
            response.message = self._response_message
        else:
            response.success = False
            response.message = "The ws server is error"
        return response

    def ws_service_callback(self, response):
        self._success_status = response['success']
        self._response_message = response['message']
        self._is_ws_service_server_correct_response = True

    def ws_service_error_callback(self, error_message):
        self._is_ws_service_server_correct_response = False

    def handle_reconnection(self):
        if time.time() - self._timestamp > self.ws_reconnection_period: 
            if not self.ws_client.is_connected:
                rospy.logwarn("Unable to connect to the server! Retrying...")
                self.connect()
                self.websocket_subscriber()
                self.advertise_topics()
            self._timestamp = time.time()

def main():
    init = RosBridgeConnector()
    init.connect()
    init.websocket_subscriber()
    init.advertise_topics()
    rate = rospy.Rate(1)
    while not rospy.is_shutdown():
        init.handle_reconnection()
        rate.sleep()
    init.unadvertise_topics()
    init.terminate()
    
if __name__ == '__main__':
    main()