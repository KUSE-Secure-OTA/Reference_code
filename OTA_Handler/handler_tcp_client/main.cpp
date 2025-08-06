#include <CommonAPI/CommonAPI.hpp>
#include <v0/commonapi/Handler_msgProxy.hpp>
#include <v0/commonapi/Handler_msg_exterProxy.hpp>
#include <openssl/cmac.h>
#include <openssl/evp.h>
#include <iostream>
#include <thread>
#include <chrono>
#include <fstream>
#include <string>
#include <condition_variable>
#include <mutex>
#include <filesystem>
#include <vector>
#include <json.hpp>

using namespace v0::commonapi;
using json = nlohmann::json;

std::mutex mtx;
std::condition_variable cv;
bool exitFlag = false;
std::vector<CommonAPI::ByteBuffer> splitIntoChunk(const CommonAPI::ByteBuffer& data, size_t chunkSize);
void processListJsonLoop();

std::string chunkStatusFilePath_ = "/opt/OTA_Handler/handler_tcp_client/chunkStatusFile.txt";

CommonAPI::ByteBuffer calculate_cmac(const uint8_t* data, size_t data_len) {
    CommonAPI::ByteBuffer mac_buffer;
    
    EVP_MAC* mac = EVP_MAC_fetch(NULL, "CMAC", NULL);
    if (!mac) return mac_buffer;

    EVP_MAC_CTX* ctx = EVP_MAC_CTX_new(mac);
    if(!ctx) {
        EVP_MAC_free(mac);
        return mac_buffer;
    }

    int8_t key[16] = {
        0x00, 0x01, 0x02, 0x03,
        0x04, 0x05, 0x06, 0x07,
        0x08, 0x09, 0x0A, 0x0B,
        0x0C, 0x0D, 0x0E, 0x0F
    };

    OSSL_PARAM params[] = {
        OSSL_PARAM_construct_utf8_string("cipher", (char*)"AES-128-CBC", 0),
        OSSL_PARAM_construct_octet_string("key", (void*)key, sizeof(key)),
        OSSL_PARAM_END
    };

    //const EVP_CIPHER* cipher = EVP_aes_128_cbc();

    unsigned char mac_tmp[EVP_MAX_BLOCK_LENGTH];
    size_t mac_len = 0;

    if (EVP_MAC_init(ctx, NULL, 0, params) &&
        EVP_MAC_update(ctx, reinterpret_cast<const unsigned char*>(data), data_len) &&
        EVP_MAC_final(ctx, mac_tmp, &mac_len, sizeof(mac_tmp))) {
            mac_buffer.assign(mac_tmp, mac_tmp + mac_len);
        }

    EVP_MAC_CTX_free(ctx);
    EVP_MAC_free(mac);
    return mac_buffer;
}

int main(){
    CommonAPI::Runtime::setProperty("LogContext", "E01S");
    CommonAPI::Runtime::setProperty("LogApplication", "E01S");
    CommonAPI::Runtime::setProperty("LibraryBase", "handler_tcp_client");
    std::shared_ptr < CommonAPI::Runtime > runtime = CommonAPI::Runtime::get();
    int counter = 0;
    int file_N = 0;
    int file_Total = 0;
    int chunkN = 0;
    int chunkTotal = 0;

    // 0 = true, 1 = false
    int ic = 0;
    int hu = 1;

    std::string domain = "local";
    std::string instance = "commonapi.Handler_msg";
    std::string instance_exter = "commonapi.Handler_msg_exter";

    std::shared_ptr<Handler_msgProxy<>> myProxy_inter = runtime->buildProxy<Handler_msgProxy>(domain, instance);
    std::cout << "Checking inter availability!" << std::endl;
    std::thread watcher(processListJsonLoop);

    if (ic == 0){
        while (!myProxy_inter->isAvailable()){
            std::this_thread::sleep_for(std::chrono::microseconds(1000));
            if(counter % 100 == 0)
                std::cout << "inter not available..."<< counter << std::endl;
            counter++;
            if (counter > 10000) {
                std::cout << "Proxy is not available, exiting..." << std::endl;
                return -1;
            }
        }
    }

    if (!std::filesystem::exists(chunkStatusFilePath_)){
        std::ofstream create_file(chunkStatusFilePath_);
        create_file << "0/0"<<std::endl;
        create_file.close();
    }else{
        std::ifstream file(chunkStatusFilePath_);
        std::string line;
        if(std::getline(file, line)){
            size_t slash = line.find('/');
            if (slash != std::string::npos){
                file_N = std::stoi(line.substr(0,slash));
                file_Total = std::stoi(line.substr(slash + 1));
            }
        }
        if(file_N != file_Total){

        }
        file.close();
    }
    

    std::shared_ptr<Handler_msg_exterProxy<>> myProxy_exter = runtime->buildProxy<Handler_msg_exterProxy>(domain, instance_exter);
    std::cout << "Checking exter availability!" << std::endl;

    if (hu == 0){
        while (!myProxy_exter->isAvailable()){
            std::this_thread::sleep_for(std::chrono::microseconds(1000));    
            std::string instance_exter = "commonapi.Handler_msg_exter";
            if(counter % 100 == 0)
                std::cout << "exter not available..."<< counter << std::endl;
            counter++;
            if (counter > 10000) {
                std::cout << "Proxy is not available, exiting..." << std::endl;
                return -1;
            }
        }
    }


    std::cout << "Available..." << std::endl;
    std::string updatePath = "./handler_tcp_client/update";

    myProxy_exter->getHandlerStatusExterEvent().subscribe([&](int32_t statusCode) {
        std::cout << "[Client] Received ServerStatusBroadcast from exter :" << statusCode << std::endl;

        CommonAPI::ByteBuffer udsRequest;
        switch (statusCode) {
            case 0: //IDLE
                // If the Master ECU downloads the update file
                if (std::filesystem::exists("./handler_tcp_client/update/HU.json")){
                    udsRequest = {0x33};
                    std::cout << "Status: 0\n\n" << std::endl;

                    myProxy_exter->updateMsgExterAsync(udsRequest, 
                        [](const CommonAPI::CallStatus& status, CommonAPI::ByteBuffer result) {
                        std::cout << "Send Request1\n\n" << std::endl;
                        if (result[0] == 0x7F) {
                            std::cout << "Negative Response\n" << std::endl;
                        }
                        else {
                            std::cout << "Positive Response 0x" << std::hex << static_cast<int>(result[0]) << std::dec << std::endl;
                        }
                    });
                    break;
                }
                else {
                    std::cout << "\nNO UPDATE\n" << std:: endl;
                    break;
                }
            case 1: {// INIT
                // RequestDownload(0x34)
                //udsRequest.push_back(0x34);
                udsRequest = {0x34};
                std::cout << "Status: 1\n\n" << std::endl;

                std::ifstream file("./handler_tcp_client/update/HU.json", std::ios::binary);
                json j;

                if(!file.is_open()){
                    std::cerr << "cannot open HU.json" <<std::endl;
                    break;
                }
                try{
                    file >> j;
                    file.close();
                }catch(json::parse_error& e){
                    std::cerr << "json parsing error: " <<e.what() << std::endl;
                    break;
                }

                // Check the new file on update directory
                std::filesystem::path baseDir = std::filesystem::current_path();
                std::filesystem::path interDir = "handler_tcp_client/update";
                baseDir = baseDir / interDir;
                std::cout << "current_dir: " << baseDir <<std::endl;
                size_t numInDir = 0;
                if(j.contains("files")&&j["files"].is_array()){
                    for(auto& file : j["files"]){
                        std::string filename = file.value("name", "");
                        if (filename.empty()){
                            std::cerr << "%%%%% Empty File Name %%%%%" <<std::endl;
                            continue;
                        }
                        std::filesystem::path filePath = baseDir / filename;
                        if(std::filesystem::exists(filePath)){
                            std::cout<<"Exist: "<<filePath<<std::endl;
                            file["status"] = "0/0";
                            numInDir ++;
                        }else{
                            std::cerr<<"Not Exitst: "<<filePath<<std::endl;
                        }
                        std::ofstream output("./handler_tcp_client/update/HU.json");
                        if(!output.is_open()){
                            std::cerr << "cannot open list.json" <<std::endl;
                            break;
                        }
                        output<<j.dump(4);
                        output.close();
                    }

                    // After check all new files, transfer messsage(0x34)
                    if(j["files"].size() == numInDir){
                        udsRequest = {0x34};
                        std::string jsonStr = j.dump(4);
                        udsRequest.insert(udsRequest.end(), jsonStr.begin(), jsonStr.end());
                        std::cout<<numInDir<<"/"<<j["files"].size()<<std::endl;
                        myProxy_exter->updateMsgExterAsync(udsRequest, 
                            [](const CommonAPI::CallStatus& status, CommonAPI::ByteBuffer result) {
                            std::cout << "Send Request1\n\n" << std::endl;
                            if (result[0] == 0x7F) {
                                std::cout << "Negative Response1\n" << std::endl;
                            }
                            else {
                                std::cout << "Positive Response 0x" << std::hex << static_cast<int>(result[0]) << std::dec << std::endl;
                            }
                        });
                        std::ofstream file(chunkStatusFilePath_);
                        file << "0/" << std::to_string(numInDir)<<std::endl;
                        file.close();
                    }

                }else{
                    std::cerr<<"Empty Array: "<< std::endl;
                }

                break;
            }
            case 2: {// WAIT
                int32_t chunkSize = 40000;

                // Read update list json file
                std::ifstream file("./handler_tcp_client/update/HU.json", std::ios::binary);
                json j;

                if(!file.is_open()){
                    std::cerr << "cannot open list.json" <<std::endl;
                    break;
                }
                try{
                    file >> j;
                    file.close();
                }catch(json::parse_error& e){
                    std::cerr << "json parsing error: " <<e.what() << std::endl;
                    break;
                }

                std::filesystem::path baseDir = std::filesystem::current_path();
                std::filesystem::path interDir = "handler_tcp_client/update";
                baseDir = baseDir / interDir;
                if(j.contains("files")&&j["files"].is_array()){
                    int8_t completeFile = 0;
                    // Transfer all update file to the target ECU
                    for(auto& file : j["files"]){
                        udsRequest = {0x36};
                        std::string sta = file.value("status","");
                        size_t slash = sta.find('/');
                        if (slash != std::string::npos){
                            chunkN = std::stoi(sta.substr(0,slash));
                            chunkTotal = std::stoi(sta.substr(slash + 1));
                            std::cout << "chunkN : "<<chunkN << " chunkTotal:" <<chunkTotal<<std::endl;
                        }

                        // When the transferring of one file end,
                        if(chunkN != 0 && chunkTotal !=0 &&chunkN == chunkTotal){
                            completeFile++;
                            if (completeFile == j["files"].size()) {
                                std::cout << "\n\t\t\tInstallation Finished\n" << std::endl;

                                // If transferring process end, TransferExit(0x37)
                                udsRequest = {0x37};
                                myProxy_exter->updateMsgExterAsync(udsRequest, 
                                    [](const CommonAPI::CallStatus& status, CommonAPI::ByteBuffer result){
                                    std::cout << "Send Request3\n\n" << std::endl;
                                    if (result[0] == 0x7F) {
                                        std::cout << "Negative Response\n" << std::endl;
                                    }
                                    else {
                                        std::cout << "Positive Response 0x" << std::hex << static_cast<int>(result[0]) << std::dec << std::endl;
                                    }
                                });
                                std::filesystem::path filepath_List = "./handler_tcp_client/update/HU.json";
                                if(std::filesystem::remove(filepath_List)){
                                    std::cout<<"list json deleted"<<std::endl;
                                }else{
                                    std::cerr<<"list json deleted failed"<<std::endl;
                                }
                                break;
                            }
                            else continue;
                        }

                        std::string filename = file.value("name", "");
                        uint8_t name_length = static_cast<uint8_t>(filename.length());
                        if (filename.empty()){
                            std::cerr << "%%%%% Empty File Name %%%%%" <<std::endl;
                            continue;
                        }
                        std::filesystem::path filePath = baseDir / filename;
                        if(std::filesystem::exists(filePath)){
                            std::cout<<"Exist: "<<filePath<<std::endl;
                        }else{
                            std::cerr<<"Not Exitst: "<<filePath<<std::endl;
                        }

                        std::ifstream file_(filePath, std::ios::binary);
                        CommonAPI::ByteBuffer chunk((std::istreambuf_iterator<char>(file_)), {});
                        std::cout << "chunk size :" << sizeof(chunk) << " \t" <<chunk.size()<<std::endl;
                        std::vector<CommonAPI::ByteBuffer> chunks = splitIntoChunk(chunk, chunkSize);
                        int32_t total_n = chunks.size();
                        std::cout << total_n <<std::endl;
                        if(chunkN < total_n) {
                            udsRequest.push_back(total_n);
                            udsRequest.push_back(chunkN);
                            udsRequest.push_back(name_length);
                            std::cout << "file name length: " <<name_length <<std::endl;
                            udsRequest.insert(udsRequest.end(), filename.begin(), filename.end());
                            std::cout << "filename: " <<filename<<std::endl;
                            udsRequest.insert(udsRequest.end(), chunks[chunkN].begin(),chunks[chunkN].end());

                            size_t msgLen = sizeof(chunks[chunkN]);

                            CommonAPI::ByteBuffer cmac = calculate_cmac(chunks[chunkN].data(), msgLen);
                            size_t mac_len = 0;
                            
                            // if(!calculate_cmac(chunks[chunkN].data(), msgLen, mac, mac_len)) {
                            //     std::cerr << "Fail to generate CMAC" << std::endl;
                            // }

                            std::cout << "CMAC: ";
                            for (auto byte : cmac) {
                                std::cout << std::hex <<std::uppercase << static_cast<int>(byte) << " ";
                            }
                            std::cout << std::endl;

                            std::cout << "CMAC LEN: " << sizeof(cmac) << ":"<<mac_len<< std::endl;
                            udsRequest.insert(udsRequest.end(), cmac.begin(), cmac.end());
        
                            CommonAPI::CallStatus callStatus;
                            CommonAPI::ByteBuffer result;
                            myProxy_exter->updateMsgExter(udsRequest, callStatus, result);
                            std::cout << "Send Request2 ## chunks number "<<chunkN<<"out of "<<total_n << std::endl;
                            if (callStatus == CommonAPI::CallStatus::SUCCESS){
                                if (result[0] == 0x7F) {
                                    std::cout << "Negative Response\n" << std::endl;
                                }
                                else {
                                    std::cout << "Positive Response 0x" << std::hex << static_cast<int>(result[0]) << std::dec << std::endl;
                                    chunkN = static_cast<int>(result[1]);
                                    std::cout << "chunkN is " <<chunkN<<std::endl;
                                    file["status"] = std::to_string(chunkN) + "/" + std::to_string(total_n);
                                    std::ofstream output("./handler_tcp_client/update/HU.json");
                                    if(!output.is_open()){
                                        std::cerr << "cannot open list.json" <<std::endl;
                                        break;
                                    }
                                    output<<j.dump(4);
                                    output.close();
                                }
                            }else{
                                std::cerr << "CallStatus Failed"<<std::endl;
                            }
                            std::string stat = std::to_string(chunkN) + "/" + std::to_string(total_n);
                            file["status"] = stat;
                        }
                        
                        break;

                        // verify and change chunkN to 0/0
                        
                    }

                }else{
                    std::cerr<<"Empty Array: "<< std::endl;
                }

                // }

            }
            case 3: // PROCESSING
                break;
            case 4: // VERIFY
         
                break;
            case 5: // READY
                break;
            case 6: {// ACTIVATE
                std::filesystem::path filepath = "./handler_tcp_client/update/HU.json";
                if(std::filesystem::remove(filepath)){
                    std::cout<<"list json deleted"<<std::endl;
                }else{
                    std::cerr<<"list json deleted failed"<<std::endl;
                }
                break;
            }
            case 7: // ERROR
                std::cout<<"%%%%% Activate Error %%%%%" <<std::endl;
                break;
            default:
                break;
        }
    });

    int32_t n = 0;

    myProxy_inter->getHandlerStatusEvent().subscribe([&](int32_t statusCode) {
        std::cout << "[Client] Received ServerStatusBroadcast from inter: " << statusCode << std::endl;

        CommonAPI::ByteBuffer udsRequest;
        switch (statusCode) {
            case 0: //IDLE
                // If the Master ECU downloads the update file
                if (std::filesystem::exists("./handler_tcp_client/update/IC.json")){
                    udsRequest = {0x33};
                    std::cout << "Status: 0\n\n" << std::endl;

                    myProxy_inter->updateMsgAsync(udsRequest, 
                        [](const CommonAPI::CallStatus& status, CommonAPI::ByteBuffer result) {
                        std::cout << "Send Request1\n\n" << std::endl;
                        if (result[0] == 0x7F) {
                            std::cout << "Negative Response\n" << std::endl;
                        }
                        else {
                            std::cout << "Positive Response 0x" << std::hex << static_cast<int>(result[0]) << std::dec << std::endl;
                        }
                    });
                    break;
                }
                else {
                    std::cout << "\nNO UPDATE\n" << std:: endl;
                    break;
                }
            case 1: {// INIT
                // RequestDownload(0x34)
                //udsRequest.push_back(0x34);
                udsRequest = {0x34};
                std::cout << "Status: 1\n\n" << std::endl;

                std::ifstream file("./handler_tcp_client/update/IC.json", std::ios::binary);
                json j;

                if(!file.is_open()){
                    std::cerr << "cannot open IC.json" <<std::endl;
                    break;
                }
                try{
                    file >> j;
                    file.close();
                }catch(json::parse_error& e){
                    std::cerr << "json parsing error: " <<e.what() << std::endl;
                    break;
                }

                // Check the new file on update directory
                std::filesystem::path baseDir = std::filesystem::current_path();
                std::filesystem::path interDir = "handler_tcp_client/update";
                baseDir = baseDir / interDir;
                std::cout << "current_dir: " << baseDir <<std::endl;
                size_t numInDir = 0;
                if(j.contains("files")&&j["files"].is_array()){
                    for(auto& file : j["files"]){
                        std::string filename = file.value("name", "");
                        if (filename.empty()){
                            std::cerr << "%%%%% Empty File Name %%%%%" <<std::endl;
                            continue;
                        }
                        std::filesystem::path filePath = baseDir / filename;
                        if(std::filesystem::exists(filePath)){
                            std::cout<<"Exist: "<<filePath<<std::endl;
                            file["status"] = "0/0";
                            numInDir ++;
                        }else{
                            std::cerr<<"Not Exitst: "<<filePath<<std::endl;
                        }
                        std::ofstream output("./handler_tcp_client/update/IC.json");
                        if(!output.is_open()){
                            std::cerr << "cannot open list.json" <<std::endl;
                            break;
                        }
                        output<<j.dump(4);
                        output.close();
                    }

                    // After check all new files, transfer messsage(0x34)
                    if(j["files"].size() == numInDir){
                        udsRequest = {0x34};
                        std::string jsonStr = j.dump(4);
                        udsRequest.insert(udsRequest.end(), jsonStr.begin(), jsonStr.end());
                        std::cout<<numInDir<<"/"<<j["files"].size()<<std::endl;
                        myProxy_inter->updateMsgAsync(udsRequest, 
                            [](const CommonAPI::CallStatus& status, CommonAPI::ByteBuffer result) {
                            std::cout << "Send Request1\n\n" << std::endl;
                            if (result[0] == 0x7F) {
                                std::cout << "Negative Response1\n" << std::endl;
                            }
                            else {
                                std::cout << "Positive Response 0x" << std::hex << static_cast<int>(result[0]) << std::dec << std::endl;
                            }
                        });
                        std::ofstream file(chunkStatusFilePath_);
                        file << "0/" << std::to_string(numInDir)<<std::endl;
                        file.close();
                    }

                }else{
                    std::cerr<<"Empty Array: "<< std::endl;
                }

                break;
            }
            case 2: {// WAIT
                int32_t chunkSize = 40000;

                // Read update list json file
                std::ifstream file("./handler_tcp_client/update/IC.json", std::ios::binary);
                json j;

                if(!file.is_open()){
                    std::cerr << "cannot open list.json" <<std::endl;
                    break;
                }
                try{
                    file >> j;
                    file.close();
                }catch(json::parse_error& e){
                    std::cerr << "json parsing error: " <<e.what() << std::endl;
                    break;
                }

                std::filesystem::path baseDir = std::filesystem::current_path();
                std::filesystem::path interDir = "handler_tcp_client/update";
                baseDir = baseDir / interDir;
                if(j.contains("files")&&j["files"].is_array()){
                    int8_t completeFile = 0;
                    // Transfer all update file to the target ECU
                    for(auto& file : j["files"]){
                        udsRequest = {0x36};
                        std::string sta = file.value("status","");
                        size_t slash = sta.find('/');
                        if (slash != std::string::npos){
                            chunkN = std::stoi(sta.substr(0,slash));
                            chunkTotal = std::stoi(sta.substr(slash + 1));
                            std::cout << "chunkN : "<<chunkN << " chunkTotal:" <<chunkTotal<<std::endl;
                        }

                        // When the transferring of one file end,
                        if(chunkN != 0 && chunkTotal !=0 &&chunkN == chunkTotal){
                            completeFile++;
                            if (completeFile == j["files"].size()) {
                                std::cout << "\n\t\t\tInstallation Finished\n" << std::endl;

                                // If transferring process end, TransferExit(0x37)
                                udsRequest = {0x37};
                                myProxy_inter->updateMsgAsync(udsRequest, 
                                    [](const CommonAPI::CallStatus& status, CommonAPI::ByteBuffer result){
                                    std::cout << "Send Request3\n\n" << std::endl;
                                    if (result[0] == 0x7F) {
                                        std::cout << "Negative Response\n" << std::endl;
                                    }
                                    else {
                                        std::cout << "Positive Response 0x" << std::hex << static_cast<int>(result[0]) << std::dec << std::endl;
                                    }
                                });
                                std::filesystem::path filepath_List = "./handler_tcp_client/update/IC.json";
                                if(std::filesystem::remove(filepath_List)){
                                    std::cout<<"list json deleted"<<std::endl;
                                }else{
                                    std::cerr<<"list json deleted failed"<<std::endl;
                                }
                                break;
                            }
                            else continue;
                        }

                        std::string filename = file.value("name", "");
                        uint8_t name_length = static_cast<uint8_t>(filename.length());
                        if (filename.empty()){
                            std::cerr << "%%%%% Empty File Name %%%%%" <<std::endl;
                            continue;
                        }
                        std::filesystem::path filePath = baseDir / filename;
                        if(std::filesystem::exists(filePath)){
                            std::cout<<"Exist: "<<filePath<<std::endl;
                        }else{
                            std::cerr<<"Not Exitst: "<<filePath<<std::endl;
                        }

                        std::ifstream file_(filePath, std::ios::binary);
                        CommonAPI::ByteBuffer chunk((std::istreambuf_iterator<char>(file_)), {});
                        std::cout << "chunk size :" << sizeof(chunk) << " \t" <<chunk.size()<<std::endl;
                        std::vector<CommonAPI::ByteBuffer> chunks = splitIntoChunk(chunk, chunkSize);
                        int32_t total_n = chunks.size();
                        std::cout << total_n <<std::endl;
                        if(chunkN < total_n) {
                            udsRequest.push_back(total_n);
                            udsRequest.push_back(chunkN);
                            udsRequest.push_back(name_length);
                            std::cout << "file name length: " <<name_length <<std::endl;
                            udsRequest.insert(udsRequest.end(), filename.begin(), filename.end());
                            std::cout << "filename: " <<filename<<std::endl;
                            udsRequest.insert(udsRequest.end(), chunks[chunkN].begin(),chunks[chunkN].end());

                            size_t msgLen = sizeof(chunks[chunkN]);

                            CommonAPI::ByteBuffer cmac = calculate_cmac(chunks[chunkN].data(), msgLen);
                            size_t mac_len = 0;
                            
                            // if(!calculate_cmac(chunks[chunkN].data(), msgLen, mac, mac_len)) {
                            //     std::cerr << "Fail to generate CMAC" << std::endl;
                            // }

                            std::cout << "CMAC: ";
                            for (auto byte : cmac) {
                                std::cout << std::hex <<std::uppercase << static_cast<int>(byte) << " ";
                            }
                            std::cout << std::endl;

                            std::cout << "CMAC LEN: " << sizeof(cmac) << ":"<<mac_len<< std::endl;
                            udsRequest.insert(udsRequest.end(), cmac.begin(), cmac.end());
        
                            CommonAPI::CallStatus callStatus;
                            CommonAPI::ByteBuffer result;
                            myProxy_inter->updateMsg(udsRequest, callStatus, result);
                            std::cout << "Send Request2 ## chunks number "<<chunkN<<"out of "<<total_n << std::endl;
                            if (callStatus == CommonAPI::CallStatus::SUCCESS){
                                if (result[0] == 0x7F) {
                                    std::cout << "Negative Response\n" << std::endl;
                                }
                                else {
                                    std::cout << "Positive Response 0x" << std::hex << static_cast<int>(result[0]) << std::dec << std::endl;
                                    chunkN = static_cast<int>(result[1]);
                                    std::cout << "chunkN is " <<chunkN<<std::endl;
                                    file["status"] = std::to_string(chunkN) + "/" + std::to_string(total_n);
                                    std::ofstream output("./handler_tcp_client/update/IC.json");
                                    if(!output.is_open()){
                                        std::cerr << "cannot open list.json" <<std::endl;
                                        break;
                                    }
                                    output<<j.dump(4);
                                    output.close();
                                }
                            }else{
                                std::cerr << "CallStatus Failed"<<std::endl;
                            }
                            std::string stat = std::to_string(chunkN) + "/" + std::to_string(total_n);
                            file["status"] = stat;
                        }
                        
                        break;

                        // verify and change chunkN to 0/0
                        
                    }

                }else{
                    std::cerr<<"Empty Array: "<< std::endl;
                }

                // }

            }
            case 3: // PROCESSING
                break;
            case 4: // VERIFY
         
                break;
            case 5: // READY
                break;
            case 6: {// ACTIVATE
                std::filesystem::path filepath = "./handler_tcp_client/update/IC.json";
                if(std::filesystem::remove(filepath)){
                    std::cout<<"list json deleted"<<std::endl;
                }else{
                    std::cerr<<"list json deleted failed"<<std::endl;
                }
                break;
            }
            case 7: // ERROR
                std::cout<<"%%%%% Activate Error %%%%%" <<std::endl;
                break;
            default:
                break;
        }
    }); 

    {
        std::unique_lock<std::mutex> lock(mtx);
        cv.wait(lock, [&]() { return exitFlag; });
    }

    watcher.join();
    return 0;

}

std::vector<CommonAPI::ByteBuffer> splitIntoChunk(const CommonAPI::ByteBuffer& data, size_t chunkSize){
    CommonAPI::ByteBuffer fileData = data;
    std::vector<CommonAPI::ByteBuffer> chunks;
    if (fileData.size() % chunkSize != 0) {
        std::cout << "before padded chunk:" <<fileData.size()<<std::endl;
        int padLen = chunkSize - (fileData.size() % chunkSize);
        fileData.insert(fileData.end(), padLen-2, static_cast<uint8_t>(0xFF));
        fileData.push_back(static_cast<uint8_t>(padLen & 0xFF));
        fileData.push_back(static_cast<uint8_t>(padLen >> 8) & 0xFF);
    }

    std::cout << "\nAfter padding: " << fileData.size() << std::endl;

    size_t offset = 0;
    size_t totalSize = fileData.size();

    while(offset < totalSize){
        size_t currentSize = std::min(chunkSize, totalSize-offset);
        chunks.emplace_back(fileData.begin()+offset, fileData.begin()+offset+currentSize);
        offset += currentSize;
    }
    std::cout<<"Total Number of Chunks: "<<chunks.size()<<std::endl;
    return chunks;
}

void processListJsonLoop() {
    while (true) {
        if (std::filesystem::exists("./handler_tcp_client/update/list.json")) {
            std::ifstream inputFile("./handler_tcp_client/update/list.json");
            if (inputFile.is_open()) {
                json listJson;
                try {
                    inputFile >> listJson;
                } catch (const std::exception& e) {
                    std::cerr << "list.JSON Failed " << e.what() << std::endl;
                    inputFile.close();
                    std::this_thread::sleep_for(std::chrono::seconds(2));
                    continue;
                }
                inputFile.close();

                if (listJson.contains("IC_files")) {
                    json icJson;
                    icJson["files"] = listJson["IC_files"];
                    std::ofstream icOut("./handler_tcp_client/update/IC.json");
                    if (icOut.is_open()) {
                        icOut << icJson.dump(4);
                        icOut.close();
                        std::cout << "[✓] IC.json Created" << std::endl;
                    }
                }

                if (listJson.contains("HU_files")) {
                    json huJson;
                    huJson["files"] = listJson["HU_files"];
                    std::ofstream huOut("./handler_tcp_client/update/HU.json");
                    if (huOut.is_open()) {
                        huOut << huJson.dump(4);
                        huOut.close();
                        std::cout << "[✓] HU.json Created" << std::endl;
                    }
                }

                std::filesystem::remove("./handler_tcp_client/update/list.json");
                std::cout << "[✓] list.json Removed" << std::endl;
            } else {
                std::cerr << "list.json Open Failed" << std::endl;
            }
        }

        std::this_thread::sleep_for(std::chrono::seconds(2));
    }
}